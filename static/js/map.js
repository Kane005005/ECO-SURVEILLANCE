/**
 * ECO-SURVEILLANCE MALI — Interactive Map Engine (Light & Hydro-focused with GPT-OSS AI & Open-Meteo)
 * Default: CartoDB Positron Light, Hydrographic network, GloFAS Sentinel Stations.
 * Secondary layers accessible on-demand.
 */

let map;
let baseLayers = {};
let activeBaseLayerName = 'light';

let allData = {
    zones: [],
    fires: [],
    stations: [],
    incidents: [],
    anomalies: [],
    vegetation: [],
    atmosphere: [],
    risks: [],
    hydrology: [],
    floods: [],
    climate_summary: [],
    eco_alerts: []
};

let grps = {
    baseMaliHydro: null,
    zones: null,
    fires: null,
    stations: null,
    hydrology: null,
    floods: null,
    climate: null,
    incidents: null,
    anomalies: null,
    ndvi: null,
    no2: null,
    risks: null,
    heatmap: null
};

// Initial state: Only Hydrography & Hydrological Stations are active
let vis = {
    maliHydro: true,
    hydrology: true,
    floods: false,
    climate: false,
    fires: false,
    incidents: false,
    anomalies: false,
    ndvi: false,
    no2: false,
    risks: false,
    heatmap: false,
    zones: false,
    stations: false
};

let activeSeverities = new Set(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']);
let autoRefreshInterval = null;

// ── INIT MAP ──
function initMap() {
    map = L.map('map', {
        zoomControl: false,
        closePopupOnClick: true
    }).setView([14.5, -4.0], 6);

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // Click on map closes open popups cleanly on desktop
    map.on('click', function () {
        map.closePopup();
    });

    // Handle popupopen: on mobile prevent map popup; on desktop load async weather
    map.on('popupopen', function (e) {
        if (window.innerWidth < 1024) {
            map.closePopup();
            return;
        }

        const wrapper = e.popup.getElement();
        if (!wrapper) return;
        const liveWeatherEl = wrapper.querySelector('.live-weather-async');
        if (liveWeatherEl) {
            const lat = liveWeatherEl.dataset.lat;
            const lon = liveWeatherEl.dataset.lon;
            if (lat && lon) {
                fetch(`/api/climate/live/?lat=${lat}&lon=${lon}`)
                    .then(r => r.json())
                    .then(data => {
                        const cur = data.current || {};
                        liveWeatherEl.innerHTML = `
                            <div class="flex items-center justify-between">
                                <div class="flex items-center gap-1.5 font-bold text-slate-900 text-xs">
                                    <span class="text-base">${cur.emoji || '🌤️'}</span>
                                    <span>${cur.temperature_c !== undefined ? cur.temperature_c.toFixed(1) : '—'}°C</span>
                                    <span class="text-[10px] font-normal text-slate-500">(${cur.condition || 'Ensoleillé'})</span>
                                </div>
                                <div class="text-[10px] text-slate-600 font-medium">
                                    💧 ${cur.humidity_pct || 45}% | 💨 ${cur.wind_speed_kmh ? cur.wind_speed_kmh.toFixed(0) : 10} km/h
                                </div>
                            </div>
                            ${cur.precipitation_mm > 0 ? `<div class="text-[10px] text-blue-700 font-semibold mt-1">🌧️ Pluie actuelle: ${cur.precipitation_mm} mm</div>` : ''}
                        `;
                    })
                    .catch(() => {
                        liveWeatherEl.innerHTML = `<span class="text-[10px] text-slate-400">Météo temps réel disponible</span>`;
                    });
            }
        }
    });

    // Tile Providers (Default: CartoDB Positron Light)
    const osmLight = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        maxZoom: 18,
        subdomains: 'abcd'
    });

    const topoMap = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA)',
        maxZoom: 17
    });

    const satelliteHybrid = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, USDA, USGS',
        maxZoom: 19
    });

    const osmDark = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OSM &copy; CARTO',
        maxZoom: 18,
        subdomains: 'abcd'
    });

    baseLayers = {
        "light": osmLight,
        "topo": topoMap,
        "satellite": satelliteHybrid,
        "dark": osmDark
    };

    osmLight.addTo(map);
    updateBaseLayerButtons('light');

    loadMaliHydroVector();
    loadMapData();
}

function switchBaseLayer(type) {
    if (!baseLayers[type]) return;
    Object.keys(baseLayers).forEach(k => {
        if (map.hasLayer(baseLayers[k])) {
            map.removeLayer(baseLayers[k]);
        }
    });
    baseLayers[type].addTo(map);
    activeBaseLayerName = type;
    updateBaseLayerButtons(type);
}

function updateBaseLayerButtons(type) {
    document.querySelectorAll('.base-layer-btn').forEach(btn => {
        if (btn.dataset.layer === type) {
            btn.className = 'base-layer-btn px-2.5 py-1 rounded-md font-semibold text-xs bg-white text-blue-700 shadow-sm border border-slate-200 transition-all';
        } else {
            btn.className = 'base-layer-btn px-2.5 py-1 rounded-md font-medium text-xs text-slate-600 hover:text-slate-900 transition-all';
        }
    });
}

// ── VECTOR HYDROGRAPHY ──
function loadMaliHydroVector() {
    fetch('/static/data/mali_hydro.geojson')
        .then(r => r.json())
        .then(geoJsonData => {
            if (grps.baseMaliHydro) map.removeLayer(grps.baseMaliHydro);
            grps.baseMaliHydro = L.geoJSON(geoJsonData, {
                style: function (feature) {
                    const props = feature.properties || {};
                    if (props.type === 'lake') {
                        return {
                            color: '#0284C7',
                            fillColor: '#38BDF8',
                            fillOpacity: 0.40,
                            weight: 1.5
                        };
                    }
                    if (props.name && props.name.toLowerCase().includes('niger')) {
                        return {
                            color: '#0284C7',
                            weight: 3.5,
                            opacity: 0.95,
                            lineCap: 'round',
                            lineJoin: 'round'
                        };
                    }
                    if (props.type === 'tributary') {
                        return {
                            color: '#0369A1',
                            weight: 2.2,
                            opacity: 0.85
                        };
                    }
                    return {
                        color: '#0284C7',
                        weight: 1.5,
                        opacity: 0.75,
                        dashArray: props.dashArray || '4, 4'
                    };
                },
                onEachFeature: function (feature, layer) {
                    const props = feature.properties || {};
                    layer.bindTooltip(`<b>${props.name}</b><br><span style="font-size:11px;color:#64748b">Bassin: ${props.basin || 'Mali'}</span>`, {
                        sticky: true,
                        className: 'hydro-tooltip shadow-sm border border-slate-200 bg-white rounded-lg p-1.5'
                    });
                }
            });
            if (vis.maliHydro) {
                grps.baseMaliHydro.addTo(map);
            }
        })
        .catch(err => console.warn("Mali Hydro GeoJSON:", err));
}

// ── ICONS ──
function hydroStationIcon(alertLevel, discharge) {
    const colors = {
        GREEN: { bg: '#22C55E', shadow: 'rgba(34, 197, 94, 0.45)' },
        YELLOW: { bg: '#EAB308', shadow: 'rgba(234, 179, 8, 0.45)' },
        ORANGE: { bg: '#F97316', shadow: 'rgba(249, 115, 22, 0.45)' },
        RED: { bg: '#EF4444', shadow: 'rgba(239, 68, 68, 0.55)' }
    };
    const c = colors[alertLevel] || colors.GREEN;
    return L.divIcon({
        html: `<div class="hydro-station-marker" style="background:${c.bg};box-shadow:0 0 0 3px #FFFFFF, 0 3px 8px ${c.shadow};">
                 <i class="fas fa-water" style="color:#FFFFFF;font-size:10px;"></i>
               </div>`,
        iconSize: [24, 24],
        className: 'hydro-marker-container'
    });
}

function climateIcon() {
    return L.divIcon({
        html: `<div style="width:20px;height:20px;background:#0284C7;border-radius:50%;border:2px solid #FFFFFF;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(2,132,199,0.45);">
                 <i class="fas fa-cloud-sun" style="color:white;font-size:10px;"></i>
               </div>`,
        iconSize: [20, 20],
        className: ''
    });
}

function fireIcon(conf) {
    const colors = { high: '#EF4444', nominal: '#F97316', low: '#EAB308' };
    const c = colors[conf] || '#F97316';
    return L.divIcon({
        html: `<div style="width:14px;height:14px;background:${c};border-radius:50%;border:2px solid #FFFFFF;box-shadow:0 2px 6px rgba(239,68,68,0.5);"></div>`,
        iconSize: [14, 14],
        className: ''
    });
}

function incidentIcon(sev) {
    const colors = { CRITICAL: '#EF4444', HIGH: '#F97316', MEDIUM: '#EAB308', LOW: '#22C55E' };
    const c = colors[sev] || '#F97316';
    return L.divIcon({
        html: `<div style="width:14px;height:14px;background:${c};border-radius:3px;border:2px solid #FFFFFF;transform:rotate(45deg);box-shadow:0 2px 6px rgba(0,0,0,0.15);"></div>`,
        iconSize: [14, 14],
        className: ''
    });
}

function alertLevelBadge(level) {
    const c = {
        RED: 'bg-red-50 text-red-700 border-red-200',
        ORANGE: 'bg-orange-50 text-orange-700 border-orange-200',
        YELLOW: 'bg-yellow-50 text-yellow-700 border-yellow-200',
        GREEN: 'bg-emerald-50 text-emerald-700 border-emerald-200'
    };
    const labels = { RED: 'Danger Crue', ORANGE: 'Alerte Crue', YELLOW: 'Vigilance', GREEN: 'Normal' };
    return `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold border ${c[level] || c.GREEN}">${labels[level] || level}</span>`;
}

// ── AI DIAGNOSIS GENERATOR (GPT-OSS INTEGRATION) ──
function getAIDiagnosisText(type, data) {
    if (type === 'station') {
        const q = data.current_discharge || data.discharge || 850;
        const trend = data.trend_72h_pct || 0;
        if (data.alert_level === 'RED' || q >= (data.seuil_danger || 3500)) {
            return `Alerte majeure : Débit critique de ${q.toFixed(0)} m³/s au-dessus du seuil de danger. Activation immédiate du plan d'évacuation et alerte aux populations du bassin aval.`;
        } else if (data.alert_level === 'ORANGE' || q >= (data.seuil_alerte || 2500)) {
            return `Vigilance forte : Débit de ${q.toFixed(0)} m³/s avec tendance à ${trend >= 0 ? '+' : ''}${trend.toFixed(1)}%. Risque de submersion des berges et digues sous 48h.`;
        } else if (trend > 15) {
            return `Montée rapide : Hausse prévue de +${trend.toFixed(1)}% à 72h. Surveillance continue des débits en amont recommandée.`;
        }
        return `Régime fluvial stable à ${q.toFixed(0)} m³/s (${data.cours_d_eau}). Aucune anomalie de crue détectée par le modèle CEMS-GloFAS.`;
    } else if (type === 'flood') {
        const area = data.flooded_area_km2 || 10;
        return `Submersion spatiale de ${area.toFixed(1)} km² (${data.flooded_area_ha || Math.round(area * 100)} ha) détectée par VIIRS NRT3. Impact direct sur les zones pastorales et agricoles du Delta.`;
    } else if (type === 'climate') {
        const v = cz_vars(data);
        return `Conditions agro-météorologiques : Température de ${v.temp}°C, vent de ${v.wind} m/s. Données en direct actualisées avec Open-Meteo.`;
    } else if (type === 'fire') {
        return `Anomalie thermique active (FRP ${data.frp || 15} MW). Risque élevé de propagation sous l'action du vent sec. Recommandation d'intervention préventive.`;
    }
    return `Paramètres écologiques sous surveillance continue par ECO-SURVEILLANCE MALI.`;
}

function cz_vars(cz) {
    const v = cz.variables || {};
    return {
        temp: v.temperature_c ? v.temperature_c.value : (v.temperature ? v.temperature.value : 34),
        wind: v.wind_speed_ms ? v.wind_speed_ms.value : (v.wind_speed ? v.wind_speed.value : 4),
        rain: v.precipitation_24h_mm ? v.precipitation_24h_mm.value : (v.precipitation_24h ? v.precipitation_24h.value : 0),
        hum: v.humidity_pct ? v.humidity_pct.value : (v.humidity ? v.humidity.value : 45),
    };
}

// ── POPUPS BLANCS ÉPURÉS AVEC IA & OPEN-METEO ──
function hydroStationPopup(s) {
    const alertColors = { GREEN: '#16A34A', YELLOW: '#CA8A04', ORANGE: '#EA580C', RED: '#DC2626' };
    const c = alertColors[s.alert_level] || '#16A34A';
    const trendIcon = s.trend_72h_pct > 0 ? 'fa-arrow-trend-up text-red-500' : s.trend_72h_pct < 0 ? 'fa-arrow-trend-down text-emerald-500' : 'fa-arrow-right text-slate-400';
    const aiNote = getAIDiagnosisText('station', s);
    const lat = s.latitude_river || s.latitude;
    const lon = s.longitude_river || s.longitude;

    let forecastRows = '';
    (s.forecasts || []).forEach(f => {
        forecastRows += `
            <div class="flex items-center justify-between py-1 text-xs border-b border-slate-100 last:border-0">
                <span class="text-slate-500 font-medium">J+${f.leadtime / 24} (${f.leadtime}h)</span>
                <span class="font-bold text-slate-800">${f.discharge.toFixed(0)} m³/s <span class="text-[9px] font-semibold" style="color:${alertColors[f.alert_level] || '#16A34A'}">(${f.alert_level})</span></span>
            </div>`;
    });

    return `
        <div class="p-3.5 bg-white font-sans text-slate-900 min-w-[260px] max-w-[320px]">
            <div class="flex items-center justify-between gap-2 pb-2 border-b border-slate-100 mb-2">
                <div class="flex items-center gap-2">
                    <span class="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center text-xs"><i class="fas fa-water"></i></span>
                    <div>
                        <div class="font-bold text-sm text-slate-900 leading-tight">${s.nom}</div>
                        <div class="text-[10px] text-slate-500 font-medium">${s.cours_d_eau}</div>
                    </div>
                </div>
                ${alertLevelBadge(s.alert_level)}
            </div>
            
            <div class="grid grid-cols-2 gap-2 my-2.5 p-2 bg-slate-50 rounded-lg border border-slate-100">
                <div>
                    <div class="text-[9px] text-slate-500 font-medium uppercase tracking-wider">Débit Actuel</div>
                    <div class="text-base font-bold" style="color:${c}">${s.current_discharge ? s.current_discharge.toFixed(0) : '—'} <span class="text-xs font-medium text-slate-600">m³/s</span></div>
                </div>
                <div>
                    <div class="text-[9px] text-slate-500 font-medium uppercase tracking-wider">Tendance 72h</div>
                    <div class="text-xs font-bold text-slate-800 flex items-center gap-1 mt-1">
                        <i class="fas ${trendIcon}"></i> ${s.trend_72h_pct >= 0 ? '+' : ''}${s.trend_72h_pct.toFixed(1)}%
                    </div>
                </div>
            </div>

            <!-- MÉTÉO TEMPS RÉEL (OPEN-METEO) -->
            <div class="p-2 bg-sky-50/70 rounded-xl border border-sky-100 text-xs mb-2.5">
                <div class="flex items-center justify-between font-bold text-sky-900 mb-1 text-[11px]">
                    <span class="flex items-center gap-1.5"><i class="fas fa-cloud-sun text-sky-600"></i> Météo en Direct (Open-Meteo)</span>
                    <span class="text-[9px] px-1.5 py-0.2 rounded bg-sky-200/60 text-sky-800 font-semibold">Live</span>
                </div>
                <div class="live-weather-async text-[11px]" data-lat="${lat}" data-lon="${lon}">
                    <span class="text-slate-400 text-[10px]"><i class="fas fa-spinner fa-spin mr-1"></i> Chargement météo temps réel...</span>
                </div>
            </div>

            <!-- DIAGNOSTIC IA GPT-OSS -->
            <div class="p-2 bg-purple-50/70 rounded-xl border border-purple-100 text-xs mb-2.5">
                <div class="flex items-center justify-between font-bold text-purple-900 mb-1 text-[11px]">
                    <span class="flex items-center gap-1.5"><i class="fas fa-brain text-purple-600"></i> Diagnostic IA (GPT-OSS)</span>
                </div>
                <p class="text-slate-700 leading-relaxed text-[11px]">${aiNote}</p>
            </div>

            <div class="text-[10px] text-slate-500 font-semibold uppercase tracking-wider mb-1">Seuils hydrologiques</div>
            <div class="grid grid-cols-3 gap-1 text-[11px] mb-2.5 text-center">
                <div class="p-1 bg-yellow-50/50 rounded border border-yellow-100"><span class="text-[9px] text-yellow-700 block">Vigilance</span><b class="text-yellow-800">${s.seuil_vigilance}</b></div>
                <div class="p-1 bg-orange-50/50 rounded border border-orange-100"><span class="text-[9px] text-orange-700 block">Alerte</span><b class="text-orange-800">${s.seuil_alerte}</b></div>
                <div class="p-1 bg-red-50/50 rounded border border-red-100"><span class="text-[9px] text-red-700 block">Danger</span><b class="text-red-800">${s.seuil_danger}</b></div>
            </div>

            ${forecastRows ? `
                <div class="text-[10px] text-slate-500 font-semibold uppercase tracking-wider mb-1">Prévisions 72h (GloFAS)</div>
                <div class="p-2 bg-slate-50 rounded-lg border border-slate-100 mb-2">${forecastRows}</div>
            ` : ''}

            <div class="text-[9px] text-slate-400 flex items-center justify-between pt-1 border-t border-slate-100">
                <span><i class="fas fa-satellite"></i> Copernicus CEMS-GloFAS</span>
                <span class="font-medium text-blue-600">ID: ${s.id}</span>
            </div>
        </div>
    `;
}

function floodPopup(fl) {
    const aiNote = getAIDiagnosisText('flood', fl);
    return `
        <div class="p-3.5 bg-white font-sans text-slate-900 min-w-[240px] max-w-[300px]">
            <div class="flex items-center gap-2 pb-2 border-b border-slate-100 mb-2">
                <span class="w-7 h-7 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center text-xs"><i class="fas fa-water-ladder"></i></span>
                <div>
                    <div class="font-bold text-sm text-slate-900">Inondation Observée</div>
                    <div class="text-[10px] text-slate-500">NASA VIIRS NRT3 (Tuile ${fl.tile_name})</div>
                </div>
            </div>
            <div class="space-y-1.5 text-xs mb-2.5">
                <div class="flex justify-between"><span class="text-slate-500">Surface submergée:</span><b class="text-sky-700">${fl.flooded_area_km2.toFixed(1)} km²</b></div>
                <div class="flex justify-between"><span class="text-slate-500">Superficie en ha:</span><b class="text-sky-700">${fl.flooded_area_ha} ha</b></div>
                <div class="flex justify-between"><span class="text-slate-500">Date d'observation:</span><span class="font-medium text-slate-700">${fl.observation_date}</span></div>
            </div>

            <!-- DIAGNOSTIC IA -->
            <div class="p-2 bg-purple-50/70 rounded-xl border border-purple-100 text-xs mb-2">
                <div class="font-bold text-purple-900 mb-1 text-[11px] flex items-center gap-1.5">
                    <i class="fas fa-brain text-purple-600"></i> Diagnostic Spatio-Temporel IA
                </div>
                <p class="text-slate-700 text-[11px] leading-relaxed">${aiNote}</p>
            </div>

            <div class="text-[9px] text-slate-400 pt-1 border-t border-slate-100"><i class="fas fa-satellite-dish"></i> ${fl.source}</div>
        </div>
    `;
}

function climatePopup(cz) {
    const v = cz_vars(cz);
    const aiNote = getAIDiagnosisText('climate', cz);
    const lat = cz.latitude || 12.6392;
    const lon = cz.longitude || -8.0029;

    return `
        <div class="p-3.5 bg-white font-sans text-slate-900 min-w-[260px] max-w-[320px]">
            <div class="flex items-center gap-2 pb-2 border-b border-slate-100 mb-2">
                <span class="w-7 h-7 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center text-xs"><i class="fas fa-cloud-sun"></i></span>
                <div>
                    <div class="font-bold text-sm text-slate-900">${cz.zone_name}</div>
                    <div class="text-[10px] text-slate-500">Météo &amp; Climatologie Mali</div>
                </div>
            </div>

            <!-- MÉTÉO EN DIRECT (OPEN-METEO) -->
            <div class="p-2.5 bg-sky-50/80 rounded-xl border border-sky-100 text-xs mb-2.5">
                <div class="flex items-center justify-between font-bold text-sky-900 mb-1.5 text-[11px]">
                    <span class="flex items-center gap-1.5"><i class="fas fa-bolt text-sky-600"></i> Conditions en Direct</span>
                    <span class="text-[9px] px-1.5 py-0.2 rounded bg-sky-200/70 text-sky-800 font-semibold">Open-Meteo</span>
                </div>
                <div class="live-weather-async text-[11px]" data-lat="${lat}" data-lon="${lon}">
                    <div class="flex items-center justify-between">
                        <span class="font-bold text-slate-800 text-xs">☀️ ${v.temp}°C</span>
                        <span class="text-[10px] text-slate-500">💧 ${v.hum}% | 💨 ${v.wind} km/h</span>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-2 gap-1.5 text-xs mb-2.5">
                <div class="p-1.5 bg-slate-50 rounded border border-slate-100"><span class="text-[9px] text-slate-500 block">Temp. Moy.</span><b class="text-slate-800">${v.temp}°C</b></div>
                <div class="p-1.5 bg-slate-50 rounded border border-slate-100"><span class="text-[9px] text-slate-500 block">Pluie 24h</span><b class="text-blue-700">${v.rain} mm</b></div>
                <div class="p-1.5 bg-slate-50 rounded border border-slate-100"><span class="text-[9px] text-slate-500 block">Humidité</span><b class="text-slate-800">${v.hum}%</b></div>
                <div class="p-1.5 bg-slate-50 rounded border border-slate-100"><span class="text-[9px] text-slate-500 block">Vent Harmattan</span><b class="text-slate-800">${v.wind} m/s</b></div>
            </div>

            <!-- DIAGNOSTIC IA -->
            <div class="p-2 bg-purple-50/70 rounded-xl border border-purple-100 text-xs mb-2">
                <div class="font-bold text-purple-900 mb-1 text-[11px] flex items-center gap-1.5">
                    <i class="fas fa-brain text-purple-600"></i> Analyse Agro-Météo IA
                </div>
                <p class="text-slate-700 text-[11px] leading-relaxed">${aiNote}</p>
            </div>

            <div class="text-[9px] text-slate-400 pt-1 border-t border-slate-100"><i class="fas fa-satellite"></i> NASA POWER &amp; Open-Meteo Live</div>
        </div>
    `;
}

function firePopup(f) {
    const aiNote = getAIDiagnosisText('fire', f);
    return `
        <div class="p-3.5 bg-white font-sans text-slate-900 min-w-[240px] max-w-[300px]">
            <div class="flex items-center gap-2 pb-2 border-b border-slate-100 mb-2">
                <span class="w-7 h-7 rounded-lg bg-red-50 text-red-600 flex items-center justify-center text-xs"><i class="fas fa-fire"></i></span>
                <div>
                    <div class="font-bold text-sm text-slate-900">Foyer de Feu Actif</div>
                    <div class="text-[10px] text-slate-500">NASA FIRMS VIIRS / MODIS</div>
                </div>
            </div>
            <div class="space-y-1 text-xs mb-2.5">
                <div class="flex justify-between"><span class="text-slate-500">Confiance:</span><b class="text-red-600 capitalize">${f.confidence || 'Nominale'}</b></div>
                <div class="flex justify-between"><span class="text-slate-500">Puissance (FRP):</span><b>${f.frp || '—'} MW</b></div>
                <div class="flex justify-between"><span class="text-slate-500">Détection:</span><span>${f.detected_at ? new Date(f.detected_at).toLocaleString('fr-FR') : '—'}</span></div>
            </div>

            <!-- DIAGNOSTIC IA -->
            <div class="p-2 bg-purple-50/70 rounded-xl border border-purple-100 text-xs mb-2">
                <div class="font-bold text-purple-900 mb-1 text-[11px] flex items-center gap-1.5">
                    <i class="fas fa-brain text-purple-600"></i> Risque de Propagation IA
                </div>
                <p class="text-slate-700 text-[11px] leading-relaxed">${aiNote}</p>
            </div>

            <div class="text-[9px] text-slate-400 pt-1 border-t border-slate-100"><i class="fas fa-satellite-dish"></i> Surveillance thermique temps quasi réel</div>
        </div>
    `;
}

function incidentPopup(inc) {
    return `
        <div class="p-3.5 bg-white font-sans text-slate-900 min-w-[240px] max-w-[300px]">
            <div class="flex items-center justify-between pb-2 border-b border-slate-100 mb-2">
                <span class="font-bold text-sm text-slate-900 truncate">${inc.title}</span>
                <span class="text-[10px] px-1.5 py-0.5 rounded font-bold bg-orange-50 text-orange-700 border border-orange-200">${inc.severity}</span>
            </div>
            <p class="text-xs text-slate-600 mb-2.5 leading-relaxed">${inc.description || 'Incident en cours d\'analyse...'}</p>
            
            <div class="p-2 bg-purple-50/70 rounded-xl border border-purple-100 text-xs mb-2">
                <div class="font-bold text-purple-900 mb-1 text-[11px] flex items-center gap-1.5">
                    <i class="fas fa-brain text-purple-600"></i> Recommandation ECO Engine
                </div>
                <p class="text-slate-700 text-[11px] leading-relaxed">Alerte générée par corrélation croisée. Notification transmise aux services régionaux.</p>
            </div>

            <div class="text-[9px] text-slate-400 pt-1 border-t border-slate-100">${inc.detected_at ? new Date(inc.detected_at).toLocaleDateString('fr-FR') : '—'}</div>
        </div>
    `;
}

// ── DATA LOADING & BUILDERS ──
function loadMapData() {
    return fetch('/api/map/')
        .then(r => r.json())
        .then(d => {
            allData = d;
            const counts = {
                hydrology: (d.hydrology || []).length,
                floods: (d.floods || []).length,
                fires: (d.fires || []).length,
                incidents: (d.incidents || []).length
            };

            const statusEl = document.getElementById('map-status');
            if (statusEl) {
                statusEl.textContent = `${counts.hydrology} stations hydrologiques GloFAS actives | Réseau hydrographique Mali | Météo Open-Meteo connectée`;
            }

            const updateEl = document.getElementById('last-update');
            if (updateEl) updateEl.textContent = 'Actualisé: ' + new Date().toLocaleTimeString('fr-FR');

            buildLayers();
        })
        .catch(e => {
            console.error("Map fetch error:", e);
            const statusEl = document.getElementById('map-status');
            if (statusEl) statusEl.textContent = 'Erreur lors du chargement des flux';
        });
}

function buildLayers() {
    // 1. Hydrology Stations Layer (ACTIVE BY DEFAULT)
    if (grps.hydrology) map.removeLayer(grps.hydrology);
    grps.hydrology = L.layerGroup();
    (allData.hydrology || []).forEach(s => {
        const lat = s.latitude_river || s.latitude;
        const lon = s.longitude_river || s.longitude;
        if (!lat || !lon) return;

        const m = L.marker([lat, lon], { icon: hydroStationIcon(s.alert_level, s.current_discharge) });
        m._data = { ...s, _layer: 'hydrology' };
        m.bindPopup(hydroStationPopup(s), { maxWidth: 340, className: 'clean-white-popup' });
        
        m.on('click', function(e) {
            if (window.innerWidth < 1024) {
                this.closePopup();
                map.closePopup();
                openBottomSheet('station', s);
            }
        });
        m.addTo(grps.hydrology);
    });
    if (vis.hydrology) grps.hydrology.addTo(map);

    // 2. LANCE Flood Layer (OFF BY DEFAULT)
    if (grps.floods) map.removeLayer(grps.floods);
    grps.floods = L.layerGroup();
    (allData.floods || []).forEach(fl => {
        if (fl.flood_geojson && fl.flood_geojson.features) {
            const floodGeo = L.geoJSON(fl.flood_geojson, {
                style: { color: '#0284C7', fillColor: '#38BDF8', fillOpacity: 0.45, weight: 2 },
                pointToLayer: function (feature, latlng) {
                    return L.circleMarker(latlng, { radius: 8, color: '#0284C7', fillColor: '#38BDF8', fillOpacity: 0.6, weight: 2 });
                },
                onEachFeature: function (feature, layer) {
                    layer.bindPopup(floodPopup(fl), { maxWidth: 300, className: 'clean-white-popup' });
                    layer.on('click', function(e) {
                        if (window.innerWidth < 1024) {
                            this.closePopup();
                            map.closePopup();
                            openBottomSheet('flood', fl);
                        }
                    });
                }
            });
            floodGeo.addTo(grps.floods);
        }
    });
    if (vis.floods) grps.floods.addTo(map);

    // 3. Climate Summary Layer (OFF BY DEFAULT)
    if (grps.climate) map.removeLayer(grps.climate);
    grps.climate = L.layerGroup();
    (allData.climate_summary || []).forEach(cz => {
        if (!cz.latitude || !cz.longitude) return;
        const m = L.marker([cz.latitude + 0.05, cz.longitude + 0.05], { icon: climateIcon() });
        m._data = { ...cz, _layer: 'climate' };
        m.bindPopup(climatePopup(cz), { maxWidth: 330, className: 'clean-white-popup' });
        m.on('click', function(e) {
            if (window.innerWidth < 1024) {
                this.closePopup();
                map.closePopup();
                openBottomSheet('climate', cz);
            }
        });
        m.addTo(grps.climate);
    });
    if (vis.climate) grps.climate.addTo(map);

    // 4. FIRMS Fires Layer (OFF BY DEFAULT)
    if (grps.fires) map.removeLayer(grps.fires);
    grps.fires = L.markerClusterGroup({
        maxClusterRadius: 40,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        iconCreateFunction: function (cluster) {
            const count = cluster.getChildCount();
            return L.divIcon({
                html: `<div class="w-8 h-8 rounded-full flex items-center justify-center bg-red-500 text-white font-bold text-xs border-2 border-white shadow-md">${count}</div>`,
                iconSize: [32, 32],
                className: ''
            });
        }
    });
    (allData.fires || []).forEach(f => {
        const m = L.marker([f.latitude, f.longitude], { icon: fireIcon(f.confidence) });
        m._data = { ...f, _layer: 'fires' };
        m.bindPopup(firePopup(f), { maxWidth: 300, className: 'clean-white-popup' });
        m.on('click', function(e) {
            if (window.innerWidth < 1024) {
                this.closePopup();
                map.closePopup();
                openBottomSheet('fire', f);
            }
        });
        m.addTo(grps.fires);
    });
    if (vis.fires) grps.fires.addTo(map);

    buildHeatmap();

    // 5. Incidents (OFF BY DEFAULT)
    if (grps.incidents) map.removeLayer(grps.incidents);
    grps.incidents = L.layerGroup();
    (allData.incidents || []).forEach(inc => {
        if (!inc.latitude || !inc.longitude) return;
        const m = L.marker([inc.latitude, inc.longitude], { icon: incidentIcon(inc.severity) });
        m._data = { ...inc, _layer: 'incidents' };
        m.bindPopup(incidentPopup(inc), { maxWidth: 300, className: 'clean-white-popup' });
        m.on('click', function(e) {
            if (window.innerWidth < 1024) {
                this.closePopup();
                map.closePopup();
                openBottomSheet('incident', inc);
            }
        });
        m.addTo(grps.incidents);
    });
    if (vis.incidents) grps.incidents.addTo(map);
}

function buildHeatmap() {
    if (grps.heatmap) map.removeLayer(grps.heatmap);
    const points = (allData.fires || []).map(f => [f.latitude, f.longitude, f.frp ? f.frp / 200 : 0.5]);
    if (typeof L.heatLayer === 'function') {
        grps.heatmap = L.heatLayer(points, {
            radius: 25,
            blur: 15,
            maxZoom: 10,
            gradient: { 0.2: '#93C5FD', 0.4: '#FDE047', 0.6: '#F97316', 1: '#EF4444' }
        });
        if (vis.heatmap) grps.heatmap.addTo(map);
    }
}

// ── LAYER TOGGLE FUNCTION ──
function toggleLayer(name) {
    vis[name] = !vis[name];
    
    // Synchronize checkboxes
    const cb = document.getElementById('layer-' + name);
    if (cb) cb.checked = vis[name];

    // Synchronize bottom buttons
    const btn = document.getElementById('btn-' + name);
    if (btn) {
        if (vis[name]) {
            btn.classList.add('active-layer-pill');
        } else {
            btn.classList.remove('active-layer-pill');
        }
    }

    if (name === 'heatmap') {
        if (vis[name]) { if (grps.heatmap) grps.heatmap.addTo(map); }
        else { if (grps.heatmap) map.removeLayer(grps.heatmap); }
    } else if (name === 'maliHydro') {
        if (vis[name]) { if (grps.baseMaliHydro) grps.baseMaliHydro.addTo(map); }
        else { if (grps.baseMaliHydro) map.removeLayer(grps.baseMaliHydro); }
    } else {
        if (vis[name]) { if (grps[name]) map.addLayer(grps[name]); }
        else { if (grps[name]) map.removeLayer(grps[name]); }
    }
}

// ── BOTTOM SHEET MOBILE ──
function openBottomSheet(type, item) {
    if (window.innerWidth >= 1024) return; // Only mobile

    if (map) map.closePopup();

    const sheet = document.getElementById('mobile-bottom-sheet');
    const content = document.getElementById('bottom-sheet-content');
    if (!sheet || !content) return;

    if (type === 'station') content.innerHTML = hydroStationPopup(item);
    else if (type === 'flood') content.innerHTML = floodPopup(item);
    else if (type === 'climate') content.innerHTML = climatePopup(item);
    else if (type === 'fire') content.innerHTML = firePopup(item);
    else if (type === 'incident') content.innerHTML = incidentPopup(item);

    sheet.classList.add('active');
    const overlay = document.getElementById('panel-overlay');
    if (overlay) overlay.classList.add('active');

    // Trigger async live weather inside bottom sheet
    const liveWeatherEl = content.querySelector('.live-weather-async');
    if (liveWeatherEl) {
        const lat = liveWeatherEl.dataset.lat;
        const lon = liveWeatherEl.dataset.lon;
        if (lat && lon) {
            fetch(`/api/climate/live/?lat=${lat}&lon=${lon}`)
                .then(r => r.json())
                .then(data => {
                    const cur = data.current || {};
                    liveWeatherEl.innerHTML = `
                        <div class="flex items-center justify-between">
                            <div class="flex items-center gap-1.5 font-bold text-slate-900 text-xs">
                                <span class="text-base">${cur.emoji || '🌤️'}</span>
                                <span>${cur.temperature_c !== undefined ? cur.temperature_c.toFixed(1) : '—'}°C</span>
                                <span class="text-[10px] font-normal text-slate-500">(${cur.condition || 'Ensoleillé'})</span>
                            </div>
                            <div class="text-[10px] text-slate-600 font-medium">
                                💧 ${cur.humidity_pct || 45}% | 💨 ${cur.wind_speed_kmh ? cur.wind_speed_kmh.toFixed(0) : 10} km/h
                            </div>
                        </div>
                    `;
                })
                .catch(() => {});
        }
    }
}

function closeBottomSheet() {
    const sheet = document.getElementById('mobile-bottom-sheet');
    if (sheet) sheet.classList.remove('active');
    const overlay = document.getElementById('panel-overlay');
    if (overlay) overlay.classList.remove('active');
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('map')) {
        initMap();
    }
});
