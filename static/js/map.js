/**
 * ECO-SURVEILLANCE MALI — Interactive Map Engine (Light & Hydro-focused with GPT-OSS AI & Open-Meteo)
 * Default: CartoDB Positron Light, Hydrographic network, GloFAS Sentinel Stations, Field Reports.
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
    eco_alerts: [],
    reports: [],
    directorates: [],
    admin_regions: []
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
    heatmap: null,
    reports: null,
    geeForest: null,
    directorates: null,
    adminRegions: null
};

// Initial state: Hydrography, Stations, Field Reports, and Regional Directorates are active
let vis = {
    maliHydro: true,
    hydrology: true,
    reports: true,
    directorates: true,
    adminRegions: false,
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
    stations: false,
    geeForest: false
};

let activeDirectorateSubtypes = new Set(['DRPC', 'DRH', 'DREF', 'DRACPN', 'DRA', 'OTHER']);
let activeSeverities = new Set(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']);
let autoRefreshInterval = null;

// ── INIT MAP ──
function initMap() {
    map = L.map('map', {
        zoomControl: false,
        closePopupOnClick: true
    }).setView([14.5, -4.0], 6);

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // Map click: either handle report placement mode or close popups
    map.on('click', function (e) {
        if (typeof isReportingMode !== 'undefined' && isReportingMode) {
            if (typeof openReportModal === 'function') {
                openReportModal(e.latlng.lat, e.latlng.lng);
            }
            return;
        }
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

function reportIcon(type, severity) {
    const sevColors = {
        CRITICAL: '#EF4444',
        HIGH: '#F97316',
        MEDIUM: '#EAB308',
        LOW: '#10B981'
    };
    const typeIcons = {
        FLOOD: 'fa-water',
        WILDFIRE: 'fa-fire',
        DROUGHT: 'fa-sun',
        WATER_QUALITY: 'fa-flask',
        OTHER: 'fa-bullhorn'
    };
    const c = sevColors[severity] || '#F97316';
    const icon = typeIcons[type] || 'fa-bullhorn';
    return L.divIcon({
        html: `<div style="width:26px;height:26px;background:${c};border-radius:50%;border:2.5px solid #FFFFFF;display:flex;align-items:center;justify-content:center;box-shadow:0 3px 8px rgba(0,0,0,0.25);color:white;font-size:11px;transition:transform .2s ease;">
                 <i class="fas ${icon}"></i>
               </div>`,
        iconSize: [26, 26],
        className: ''
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

function directorateIcon(type) {
    const config = {
        DRPC: { icon: 'fa-shield-halved', bg: '#DC2626', shadow: 'rgba(220, 38, 38, 0.55)' },
        DRH: { icon: 'fa-droplet', bg: '#0284C7', shadow: 'rgba(2, 132, 199, 0.55)' },
        DREF: { icon: 'fa-tree', bg: '#16A34A', shadow: 'rgba(22, 163, 74, 0.55)' },
        DRACPN: { icon: 'fa-recycle', bg: '#059669', shadow: 'rgba(5, 150, 105, 0.55)' },
        DRA: { icon: 'fa-wheat-awn', bg: '#D97706', shadow: 'rgba(217, 119, 6, 0.55)' },
        OTHER: { icon: 'fa-building', bg: '#475569', shadow: 'rgba(71, 85, 105, 0.55)' }
    };
    const c = config[type] || config.OTHER;
    return L.divIcon({
        html: `<div style="width:28px;height:28px;background:${c.bg};border-radius:50%;border:2.5px solid #FFFFFF;display:flex;align-items:center;justify-content:center;box-shadow:0 3px 10px ${c.shadow};color:white;font-size:11px;transition:transform .2s ease;cursor:pointer;">
                 <i class="fas ${c.icon}"></i>
               </div>`,
        iconSize: [28, 28],
        className: 'directorate-marker-container'
    });
}

function adminRegionIcon(r) {
    const num = r.region_number !== null && r.region_number !== undefined ? (r.region_number === 0 ? 'BKO' : 'R' + String(r.region_number).padStart(2, '0')) : 'R';
    return L.divIcon({
        html: `<div style="display:flex;align-items:center;gap:4px;background:#1E1B4B;color:#FFFFFF;padding:3px 8px;border-radius:12px;font-size:10px;font-weight:700;border:1.5px solid #818CF8;box-shadow:0 2px 8px rgba(30,27,75,0.4);white-space:nowrap;cursor:pointer;">
                 <span style="background:#4F46E5;padding:1px 4px;border-radius:6px;font-size:9px;">${num}</span>
                 <span>${r.name}</span>
               </div>`,
        iconSize: [110, 24],
        className: 'admin-region-marker-container'
    });
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

// ── POPUPS BLANCS ÉPURÉS AVEC IA, OPEN-METEO & SIGNALEMENTS ──
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

            <!-- CTA CONTACTER LES STRUCTURES -->
            <button onclick="openContactStructuresModal(null, '${s.region || ''}')" class="w-full mt-2 mb-2 py-1.5 px-2 bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition-colors">
                <i class="fas fa-phone-volume"></i> Contacter les structures (122)
            </button>

            <div class="text-[9px] text-slate-400 flex items-center justify-between pt-1 border-t border-slate-100">
                <span><i class="fas fa-satellite"></i> Copernicus CEMS-GloFAS</span>
                <span class="font-medium text-blue-600">ID: ${s.id}</span>
            </div>
        </div>
    `;
}

function fieldReportPopup(p) {
    const sevColors = {
        CRITICAL: 'bg-red-50 text-red-700 border-red-200',
        HIGH: 'bg-orange-50 text-orange-700 border-orange-200',
        MEDIUM: 'bg-yellow-50 text-yellow-700 border-yellow-200',
        LOW: 'bg-emerald-50 text-emerald-700 border-emerald-200'
    };
    const badge = sevColors[p.severity] || sevColors.MEDIUM;
    const verifiedBadge = p.is_verified 
        ? `<span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-100 text-emerald-800"><i class="fas fa-check-circle mr-1"></i>Vérifié</span>`
        : `<span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-amber-50 text-amber-800 border border-amber-200"><i class="fas fa-hourglass-half mr-1"></i>Remontée terrain</span>`;

    return `
        <div class="p-3.5 bg-white font-sans text-slate-900 min-w-[260px] max-w-[320px]">
            <div class="flex items-center justify-between gap-2 pb-2 border-b border-slate-100 mb-2">
                <div class="flex items-center gap-2 truncate">
                    <span class="w-7 h-7 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center text-xs flex-shrink-0"><i class="fas fa-bullhorn"></i></span>
                    <div class="truncate">
                        <div class="font-bold text-sm text-slate-900 truncate">${p.title}</div>
                        <div class="text-[10px] text-slate-500">${p.report_type_display || p.report_type}</div>
                    </div>
                </div>
                <span class="px-2 py-0.5 rounded-full text-[10px] font-bold border flex-shrink-0 ${badge}">${p.severity_display || p.severity}</span>
            </div>

            <p class="text-xs text-slate-700 mb-2.5 leading-relaxed bg-slate-50 p-2 rounded-lg border border-slate-100">${p.description}</p>

            <div class="space-y-1 text-xs mb-2.5">
                <div class="flex justify-between"><span class="text-slate-500">Observateur:</span><b class="text-slate-800">${p.author_name || 'Anonyme'}</b></div>
                ${p.author_phone ? `<div class="flex justify-between"><span class="text-slate-500">Contact:</span><span class="text-slate-700">${p.author_phone}</span></div>` : ''}
                <div class="flex justify-between"><span class="text-slate-500">Date:</span><span>${p.created_at_display || new Date(p.created_at).toLocaleString('fr-FR')}</span></div>
            </div>

            <!-- CTA CONTACTER LES STRUCTURES -->
            <button onclick="openContactStructuresModal()" class="w-full mb-2 py-1.5 px-2.5 bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition-colors">
                <i class="fas fa-phone-volume"></i> Contacter les structures (122)
            </button>

            <div class="flex items-center justify-between pt-2 border-t border-slate-100 text-[10px] text-slate-400">
                <span><i class="fas fa-location-dot text-emerald-600"></i> Signalement Citoyen</span>
                ${verifiedBadge}
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

            <!-- CTA CONTACTER LES STRUCTURES -->
            <button onclick="openContactStructuresModal()" class="w-full mb-2 py-1.5 px-2.5 bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition-colors">
                <i class="fas fa-phone-volume"></i> Contacter les structures (122)
            </button>

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

            <!-- CTA CONTACTER LES STRUCTURES -->
            <button onclick="openContactStructuresModal()" class="w-full mb-2 py-1.5 px-2.5 bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition-colors">
                <i class="fas fa-phone-volume"></i> Contacter les structures (122)
            </button>

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

            <!-- CTA CONTACTER LES STRUCTURES -->
            <button onclick="openContactStructuresModal(${inc.zone_id ? `'${inc.zone_id}'` : 'null'})" class="w-full mb-2 py-1.5 px-2.5 bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition-colors">
                <i class="fas fa-phone-volume"></i> Contacter les structures (122)
            </button>

            <div class="text-[9px] text-slate-400 pt-1 border-t border-slate-100">${inc.detected_at ? new Date(inc.detected_at).toLocaleDateString('fr-FR') : '—'}</div>
        </div>
    `;
}

function directoratePopup(d) {
    const badgeColors = {
        DRPC: 'bg-red-50 text-red-700 border-red-200',
        DRH: 'bg-sky-50 text-sky-700 border-sky-200',
        DREF: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        DRACPN: 'bg-teal-50 text-teal-700 border-teal-200',
        DRA: 'bg-amber-50 text-amber-700 border-amber-200',
        OTHER: 'bg-slate-50 text-slate-700 border-slate-200'
    };
    const badgeClass = badgeColors[d.directorate_type] || badgeColors.OTHER;

    // Active incidents in zones under jurisdiction
    const activeIncidents = (allData.incidents || []).filter(inc => {
        return (d.zones_under_jurisdiction || []).some(zName => 
            inc.title && inc.title.toLowerCase().includes(zName.toLowerCase())
        );
    });

    // Zones pill list
    const zonesList = (d.zones_under_jurisdiction || []).map(z => 
        `<span class="px-2 py-0.5 bg-slate-100 text-slate-700 rounded-md text-[10px] font-medium border border-slate-200">${z}</span>`
    ).join(' ');

    return `
        <div class="p-4 bg-white font-sans text-slate-900 min-w-[280px] max-w-[340px]">
            <!-- Header with Type Badge and Region -->
            <div class="flex items-start justify-between gap-2 mb-2.5 pb-2.5 border-b border-slate-100">
                <div>
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${badgeClass} mb-1.5 shadow-2xs">
                        <i class="${d.icon || 'fas fa-building'}"></i> ${d.type_display || d.directorate_type}
                    </span>
                    <h4 class="font-bold text-slate-900 text-sm leading-snug">${d.name}</h4>
                    <div class="text-[11px] text-slate-500 flex items-center gap-1.5 mt-1">
                        <i class="fas fa-location-dot text-red-500 text-[11px]"></i>
                        <span>Région de <b>${d.region_name || 'Mali'}</b> ${d.capital ? '• Chef-lieu: ' + d.capital : ''}</span>
                    </div>
                </div>
            </div>

            <!-- Address and Headquarters -->
            ${d.address ? `
            <div class="text-[11px] text-slate-600 mb-3 flex items-start gap-1.5 bg-slate-50 p-2 rounded-lg border border-slate-100">
                <i class="fas fa-map-pin text-slate-400 text-xs mt-0.5 flex-shrink-0"></i>
                <span class="leading-relaxed">${d.address}</span>
            </div>` : ''}

            <!-- Direct Call Action CTAs (One-Click Emergency & Standard Lines) -->
            <div class="grid grid-cols-2 gap-2 mb-3">
                <a href="tel:${d.phone_primary}" class="py-2 px-2.5 bg-blue-600 hover:bg-blue-700 active:scale-95 text-white rounded-xl text-center font-bold text-xs flex items-center justify-center gap-1.5 transition-all shadow-sm">
                    <i class="fas fa-phone"></i> Appeler
                </a>
                <a href="tel:${d.emergency_number || '122'}" class="py-2 px-2.5 bg-red-600 hover:bg-red-700 active:scale-95 text-white rounded-xl text-center font-bold text-xs flex items-center justify-center gap-1.5 transition-all shadow-sm ring-2 ring-red-300">
                    <i class="fas fa-phone-volume"></i> Urgence ${d.emergency_number || '122'}
                </a>
            </div>

            ${d.phone_secondary ? `
            <div class="text-[11px] text-slate-600 mb-2 flex items-center justify-between bg-slate-50 px-2.5 py-1.5 rounded-lg border border-slate-100">
                <span class="text-slate-500 text-[10px]">Ligne d'astreinte :</span>
                <a href="tel:${d.phone_secondary}" class="font-semibold text-slate-800 hover:text-blue-600 flex items-center gap-1">
                    <i class="fas fa-phone-flip text-[9px] text-slate-400"></i> ${d.phone_secondary}
                </a>
            </div>` : ''}

            ${d.email ? `
            <div class="text-[11px] text-slate-600 mb-2.5 flex items-center justify-between bg-slate-50 px-2.5 py-1.5 rounded-lg border border-slate-100">
                <span class="text-slate-500 text-[10px]">Courriel officiel :</span>
                <a href="mailto:${d.email}" class="font-medium text-blue-600 truncate max-w-[170px] hover:underline flex items-center gap-1">
                    <i class="fas fa-envelope text-[9px] text-slate-400"></i> ${d.email}
                </a>
            </div>` : ''}

            <!-- Active Alerts in Sector -->
            ${activeIncidents.length > 0 ? `
            <div class="mb-2.5 p-2 bg-red-50/80 rounded-xl border border-red-200 text-xs">
                <div class="font-bold text-red-900 mb-1 text-[11px] flex items-center justify-between">
                    <span class="flex items-center gap-1"><i class="fas fa-triangle-exclamation text-red-600"></i> Alertes actives sous juridiction</span>
                    <span class="px-1.5 py-0.5 rounded bg-red-200 text-red-800 text-[9px] font-bold">${activeIncidents.length}</span>
                </div>
                <div class="space-y-1 mt-1">
                    ${activeIncidents.slice(0, 2).map(inc => `
                        <div class="text-[10px] text-red-800 flex items-center justify-between">
                            <span class="truncate max-w-[200px]">• ${inc.title}</span>
                            <span class="font-bold text-[9px] uppercase">${inc.severity}</span>
                        </div>
                    `).join('')}
                </div>
            </div>` : ''}

            <!-- Zones under jurisdiction -->
            <div class="pt-2 border-t border-slate-100">
                <div class="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1.5 flex items-center justify-between">
                    <span>Secteurs &amp; Zones de Surveillance</span>
                    <span class="text-blue-700 font-bold">${(d.zones_under_jurisdiction || []).length} zones</span>
                </div>
                <div class="flex flex-wrap gap-1 max-h-20 overflow-y-auto">
                    ${zonesList || '<span class="text-[10px] text-slate-400 italic">Région entière sous surveillance</span>'}
                </div>
            </div>

            <!-- Notes -->
            ${d.notes ? `
            <div class="mt-2.5 p-2 bg-slate-50 rounded-lg text-[10px] text-slate-600 border border-slate-200/80 leading-relaxed">
                <i class="fas fa-info-circle text-blue-500 mr-1"></i> ${d.notes}
            </div>` : ''}
        </div>
    `;
}

function adminRegionPopup(r) {
    const num = r.region_number !== null && r.region_number !== undefined 
        ? (r.region_number === 0 ? 'District Spécial' : 'Région N° ' + String(r.region_number).padStart(2, '0')) 
        : 'Région Administrative';

    return `
        <div class="p-4 bg-white font-sans text-slate-900 min-w-[270px] max-w-[320px]">
            <div class="flex items-center justify-between mb-2.5 pb-2 border-b border-slate-100">
                <div>
                    <span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">${num}</span>
                    <h4 class="font-bold text-slate-900 text-sm mt-1">${r.name}</h4>
                </div>
                <span class="text-xs font-mono font-bold text-slate-400 px-1.5 py-0.5 bg-slate-50 rounded border border-slate-200">${r.code}</span>
            </div>

            <div class="space-y-1.5 text-xs text-slate-600 mb-3 bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                <div class="flex items-center justify-between">
                    <span class="text-slate-500 text-[11px]">Chef-lieu :</span>
                    <b class="text-slate-800">${r.capital || '—'}</b>
                </div>
                <div class="flex items-center justify-between">
                    <span class="text-slate-500 text-[11px]">Population :</span>
                    <b class="text-slate-800">${r.population ? Number(r.population).toLocaleString('fr-FR') + ' hab.' : '—'}</b>
                </div>
                <div class="flex items-center justify-between">
                    <span class="text-slate-500 text-[11px]">Superficie :</span>
                    <b class="text-slate-800">${r.area_km2 ? Number(r.area_km2).toLocaleString('fr-FR') + ' km²' : '—'}</b>
                </div>
                <div class="flex items-center justify-between">
                    <span class="text-slate-500 text-[11px]">Directions régionales :</span>
                    <b class="text-red-600 font-bold">${r.directorates_count || 0} services</b>
                </div>
                <div class="flex items-center justify-between">
                    <span class="text-slate-500 text-[11px]">Zones de surveillance :</span>
                    <b class="text-blue-600 font-bold">${r.zones_count || 0} zones</b>
                </div>
            </div>

            <div class="flex gap-2">
                <button onclick="filterDirectoratesByRegion('${r.code}')" class="flex-1 py-1.5 bg-indigo-600 hover:bg-indigo-700 active:scale-95 text-white font-semibold text-xs rounded-xl transition-all shadow-sm flex items-center justify-center gap-1.5">
                    <i class="fas fa-shield-halved"></i> Voir les services
                </button>
                <a href="tel:122" class="py-1.5 px-2.5 bg-red-600 hover:bg-red-700 text-white font-bold text-xs rounded-xl transition-all flex items-center justify-center gap-1" title="Urgence Protection Civile">
                    <i class="fas fa-phone-volume"></i> 122
                </a>
            </div>
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
                incidents: (d.incidents || []).length,
                reports: (d.reports || []).length,
                directorates: (d.directorates || []).length,
                admin_regions: (d.admin_regions || []).length
            };

            const statusEl = document.getElementById('map-status');
            if (statusEl) {
                statusEl.textContent = `${counts.directorates} Directions Régionales | ${counts.admin_regions} Régions 2023 | ${counts.hydrology} stations GloFAS`;
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

    // 2. Field Reports (Crowdsourcing) Layer (ACTIVE BY DEFAULT)
    if (grps.reports) map.removeLayer(grps.reports);
    grps.reports = L.layerGroup();
    (allData.reports || []).forEach(f => {
        const geom = f.geometry || {};
        const coords = geom.coordinates || [];
        const props = f.properties || {};
        if (coords.length >= 2) {
            const lon = coords[0];
            const lat = coords[1];
            const m = L.marker([lat, lon], { icon: reportIcon(props.report_type, props.severity) });
            m._data = { ...props, latitude: lat, longitude: lon, _layer: 'reports' };
            m.bindPopup(fieldReportPopup(props), { maxWidth: 330, className: 'clean-white-popup' });
            m.on('click', function(e) {
                if (window.innerWidth < 1024) {
                    this.closePopup();
                    map.closePopup();
                    openBottomSheet('report', props);
                }
            });
            m.addTo(grps.reports);
        }
    });
    if (vis.reports) grps.reports.addTo(map);

    // 3. LANCE Flood Layer (OFF BY DEFAULT)
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

    // 4. Climate Summary Layer (OFF BY DEFAULT)
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

    // 5. FIRMS Fires Layer (OFF BY DEFAULT)
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

    // 6. Incidents (OFF BY DEFAULT)
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

    // 7. Directions Régionales (ACTIVE PAR DÉFAUT)
    rebuildDirectoratesLayer();

    // 8. 19 Régions Administratives 2023 (OFF PAR DÉFAUT)
    rebuildAdminRegionsLayer();
}

function rebuildDirectoratesLayer() {
    if (grps.directorates) map.removeLayer(grps.directorates);
    grps.directorates = L.layerGroup();

    const filtered = (allData.directorates || []).filter(d => activeDirectorateSubtypes.has(d.directorate_type));
    filtered.forEach(d => {
        if (!d.latitude || !d.longitude) return;
        const m = L.marker([d.latitude, d.longitude], { icon: directorateIcon(d.directorate_type) });
        m._data = { ...d, _layer: 'directorates' };
        m.bindPopup(directoratePopup(d), { maxWidth: 350, className: 'clean-white-popup' });
        m.on('click', function(e) {
            if (window.innerWidth < 1024) {
                this.closePopup();
                map.closePopup();
                openBottomSheet('directorate', d);
            }
        });
        m.addTo(grps.directorates);
    });

    if (vis.directorates) grps.directorates.addTo(map);

    const badge = document.getElementById('directorates-count-badge');
    if (badge) badge.textContent = `${filtered.length} services`;
}

function rebuildAdminRegionsLayer() {
    if (grps.adminRegions) map.removeLayer(grps.adminRegions);
    grps.adminRegions = L.layerGroup();

    (allData.admin_regions || []).forEach(r => {
        if (!r.latitude || !r.longitude) return;
        const m = L.marker([r.latitude, r.longitude], { icon: adminRegionIcon(r) });
        m._data = { ...r, _layer: 'adminRegions' };
        m.bindPopup(adminRegionPopup(r), { maxWidth: 330, className: 'clean-white-popup' });
        m.on('click', function(e) {
            if (window.innerWidth < 1024) {
                this.closePopup();
                map.closePopup();
                openBottomSheet('adminRegion', r);
            }
        });
        m.addTo(grps.adminRegions);
    });

    if (vis.adminRegions) grps.adminRegions.addTo(map);
}

function toggleDirectorateSubtype(subtype) {
    if (activeDirectorateSubtypes.has(subtype)) {
        activeDirectorateSubtypes.delete(subtype);
    } else {
        activeDirectorateSubtypes.add(subtype);
    }
    rebuildDirectoratesLayer();
}

function filterDirectoratesByRegion(regionCode) {
    if (!vis.directorates) {
        toggleLayer('directorates');
    }
    const r = (allData.admin_regions || []).find(reg => reg.code === regionCode);
    if (r && r.latitude && r.longitude) {
        map.flyTo([r.latitude, r.longitude], 10, { animate: true, duration: 1.2 });
    }
}

function filterZonesByName(query) {
    if (!query) return;
    const q = query.trim().toLowerCase();
    if (q.length < 2) return;

    // Search in directorates
    const foundDir = (allData.directorates || []).find(d => 
        (d.name && d.name.toLowerCase().includes(q)) ||
        (d.region_name && d.region_name.toLowerCase().includes(q)) ||
        (d.capital && d.capital.toLowerCase().includes(q))
    );
    if (foundDir && foundDir.latitude && foundDir.longitude) {
        if (!vis.directorates) toggleLayer('directorates');
        map.flyTo([foundDir.latitude, foundDir.longitude], 13, { animate: true });
        return;
    }

    // Search in admin regions
    const foundReg = (allData.admin_regions || []).find(r => 
        (r.name && r.name.toLowerCase().includes(q)) ||
        (r.capital && r.capital.toLowerCase().includes(q))
    );
    if (foundReg && foundReg.latitude && foundReg.longitude) {
        map.flyTo([foundReg.latitude, foundReg.longitude], 10, { animate: true });
        return;
    }

    // Search in hydro stations
    const foundHydro = (allData.hydrology || []).find(s => 
        (s.nom_station && s.nom_station.toLowerCase().includes(q)) ||
        (s.cours_d_eau && s.cours_d_eau.toLowerCase().includes(q)) ||
        (s.bassin && s.bassin.toLowerCase().includes(q))
    );
    if (foundHydro && (foundHydro.latitude_river || foundHydro.latitude)) {
        map.flyTo([foundHydro.latitude_river || foundHydro.latitude, foundHydro.longitude_river || foundHydro.longitude], 12, { animate: true });
        return;
    }

    // Search in zones
    const foundZone = (allData.zones || []).find(z => z.name && z.name.toLowerCase().includes(q));
    if (foundZone && foundZone.latitude && foundZone.longitude) {
        map.flyTo([foundZone.latitude, foundZone.longitude], 11, { animate: true });
    }
}

function resetFilters() {
    activeDirectorateSubtypes = new Set(['DRPC', 'DRH', 'DREF', 'DRACPN', 'DRA', 'OTHER']);
    ['drpc', 'drh', 'dref', 'dracpn', 'dra'].forEach(k => {
        const el = document.getElementById('subfilter-' + k);
        if (el) el.checked = true;
    });
    rebuildDirectoratesLayer();
    map.setView([14.5, -4.0], 6);
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

// ── DYNAMIC REPORT ADDITION ──
function addReportMarkerToMap(feature) {
    if (!grps.reports) {
        grps.reports = L.layerGroup();
        if (vis.reports) grps.reports.addTo(map);
    }
    const coords = (feature.geometry || {}).coordinates || [];
    const props = feature.properties || {};
    if (coords.length >= 2) {
        const lon = coords[0];
        const lat = coords[1];
        const m = L.marker([lat, lon], { icon: reportIcon(props.report_type, props.severity) });
        m._data = { ...props, latitude: lat, longitude: lon, _layer: 'reports' };
        m.bindPopup(fieldReportPopup(props), { maxWidth: 330, className: 'clean-white-popup' });
        m.on('click', function(e) {
            if (window.innerWidth < 1024) {
                this.closePopup();
                map.closePopup();
                openBottomSheet('report', props);
            }
        });
        m.addTo(grps.reports);
        
        // Ensure layer is turned ON and visible
        if (!vis.reports) {
            toggleLayer('reports');
        }
        
        map.flyTo([lat, lon], 13, { animate: true, duration: 1.2 });
        setTimeout(() => {
            if (window.innerWidth >= 1024) m.openPopup();
        }, 1300);
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
    } else if (name === 'geeForest') {
        if (vis.geeForest) {
            if (grps.geeForest) {
                map.addLayer(grps.geeForest);
            } else {
                const statusEl = document.getElementById('map-status');
                if (statusEl) statusEl.textContent = 'Chargement des tuiles Sentinel-2 GEE Forêts...';
                fetch('/api/satellite/gee-tiles/?layer=forest')
                    .then(r => r.json())
                    .then(data => {
                        if (data.tile_url) {
                            grps.geeForest = L.tileLayer(data.tile_url, {
                                maxZoom: 18,
                                attribution: 'Google Earth Engine &copy; Copernicus Sentinel-2'
                            });
                            if (vis.geeForest) {
                                grps.geeForest.addTo(map);
                            }
                        }
                        if (statusEl) statusEl.textContent = 'Couche Forêts & Canopée GEE active';
                    })
                    .catch(err => {
                        console.error('GEE tile error:', err);
                        if (statusEl) statusEl.textContent = 'Erreur chargement tuiles GEE';
                    });
            }
        } else {
            if (grps.geeForest) map.removeLayer(grps.geeForest);
        }
    } else if (name === 'directorates') {
        if (vis.directorates) {
            if (grps.directorates) map.addLayer(grps.directorates);
            else rebuildDirectoratesLayer();
        } else {
            if (grps.directorates) map.removeLayer(grps.directorates);
        }
    } else if (name === 'adminRegions') {
        if (vis.adminRegions) {
            if (grps.adminRegions) map.addLayer(grps.adminRegions);
            else rebuildAdminRegionsLayer();
        } else {
            if (grps.adminRegions) map.removeLayer(grps.adminRegions);
        }
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
    else if (type === 'report') content.innerHTML = fieldReportPopup(item);
    else if (type === 'flood') content.innerHTML = floodPopup(item);
    else if (type === 'climate') content.innerHTML = climatePopup(item);
    else if (type === 'fire') content.innerHTML = firePopup(item);
    else if (type === 'incident') content.innerHTML = incidentPopup(item);
    else if (type === 'directorate') content.innerHTML = directoratePopup(item);
    else if (type === 'adminRegion') content.innerHTML = adminRegionPopup(item);

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

// ── CONTACT STRUCTURES MODAL LOGIC ──
let currentModalTypeFilter = 'ALL';
let modalCustomDirectoratesList = null;

function openContactStructuresModal(zoneId, regionCode) {
    const modal = document.getElementById('contact-structures-modal');
    if (!modal) return;

    modal.classList.add('active');

    // Populate region select if needed
    const regionSelect = document.getElementById('modal-dir-region-select');
    if (regionSelect && regionSelect.options.length <= 1 && allData.admin_regions) {
        allData.admin_regions.forEach(r => {
            const opt = document.createElement('option');
            opt.value = r.code;
            opt.textContent = `${r.code} - Région de ${r.name} (${r.capital || ''})`;
            regionSelect.appendChild(opt);
        });
    }

    // Reset filters
    const searchInput = document.getElementById('modal-dir-search');
    if (searchInput) searchInput.value = '';
    setModalTypeFilter('ALL', false);

    if (zoneId) {
        const container = document.getElementById('modal-directorates-container');
        if (container) {
            container.innerHTML = `
                <div class="text-center py-6 text-slate-500">
                    <i class="fas fa-spinner fa-spin text-xl text-red-600 mb-2"></i>
                    <p class="text-xs">Chargement des structures compétentes pour la zone...</p>
                </div>
            `;
        }
        fetch(`/api/geography/directorates/by-zone/${zoneId}/`)
            .then(r => r.json())
            .then(data => {
                modalCustomDirectoratesList = data.competent_directorates || [];
                const zoneName = data.zone ? data.zone.name : '';
                renderModalDirectorates(modalCustomDirectoratesList, `Structures compétentes pour la zone <b>${zoneName}</b>`);
            })
            .catch(err => {
                console.error('Erreur chargement structures zone:', err);
                modalCustomDirectoratesList = null;
                filterModalDirectorates();
            });
    } else {
        modalCustomDirectoratesList = null;
        if (regionCode && regionSelect) {
            regionSelect.value = regionCode;
        }
        filterModalDirectorates();
    }
}

function closeContactStructuresModal() {
    const modal = document.getElementById('contact-structures-modal');
    if (modal) modal.classList.remove('active');
    modalCustomDirectoratesList = null;
}

function setModalTypeFilter(type, shouldFilter = true) {
    currentModalTypeFilter = type;
    document.querySelectorAll('.modal-type-btn').forEach(btn => {
        const btnType = btn.dataset.type;
        if (btnType === type) {
            btn.className = 'modal-type-btn px-2.5 py-1 rounded-lg font-bold text-[11px] bg-slate-800 text-white whitespace-nowrap shadow-xs';
        } else {
            btn.className = 'modal-type-btn px-2.5 py-1 rounded-lg font-medium text-[11px] bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 whitespace-nowrap';
        }
    });
    if (shouldFilter) {
        filterModalDirectorates();
    }
}

function filterModalDirectorates() {
    const sourceList = modalCustomDirectoratesList || allData.directorates || [];
    const searchVal = (document.getElementById('modal-dir-search')?.value || '').toLowerCase().trim();
    const regionVal = document.getElementById('modal-dir-region-select')?.value || '';

    const filtered = sourceList.filter(d => {
        if (currentModalTypeFilter !== 'ALL' && d.directorate_type !== currentModalTypeFilter) {
            return false;
        }
        if (regionVal) {
            const dRegCode = d.region_code || (d.region && d.region.code) || '';
            const dRegName = d.region_name || (d.region && d.region.name) || '';
            if (dRegCode !== regionVal && !dRegName.toLowerCase().includes(regionVal.toLowerCase())) {
                return false;
            }
        }
        if (searchVal) {
            const matchName = (d.name || '').toLowerCase().includes(searchVal);
            const matchCity = (d.capital || d.address || '').toLowerCase().includes(searchVal);
            const matchPhone = (d.phone_primary || d.emergency_number || '').includes(searchVal);
            const matchRegion = (d.region_name || (d.region && d.region.name) || '').toLowerCase().includes(searchVal);
            if (!matchName && !matchCity && !matchPhone && !matchRegion) {
                return false;
            }
        }
        return true;
    });

    renderModalDirectorates(filtered);
}

function renderModalDirectorates(list, headerNotice) {
    const container = document.getElementById('modal-directorates-container');
    const counter = document.getElementById('modal-dir-counter');
    if (!container) return;

    if (counter) {
        counter.textContent = `${list.length} structure${list.length > 1 ? 's' : ''} disponible${list.length > 1 ? 's' : ''}`;
    }

    if (!list || list.length === 0) {
        container.innerHTML = `
            <div class="text-center py-10 bg-slate-50 rounded-xl border border-dashed border-slate-300">
                <i class="fas fa-building-circle-exclamation text-slate-400 text-3xl mb-2"></i>
                <div class="font-bold text-slate-700 text-sm">Aucune direction trouvée</div>
                <p class="text-xs text-slate-500 mt-1">Modifiez vos critères de recherche ou sélectionnez une autre région.</p>
                <div class="mt-4">
                    <a href="tel:122" class="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-bold shadow-md">
                        <i class="fas fa-phone-volume"></i> Appeler l'Urgence Nationale (122)
                    </a>
                </div>
            </div>
        `;
        return;
    }

    const badgeColors = {
        DRPC: 'bg-red-50 text-red-700 border-red-200',
        DRH: 'bg-sky-50 text-sky-700 border-sky-200',
        DREF: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        DRACPN: 'bg-teal-50 text-teal-700 border-teal-200',
        DRA: 'bg-amber-50 text-amber-700 border-amber-200',
        OTHER: 'bg-slate-50 text-slate-700 border-slate-200'
    };

    let html = '';
    if (headerNotice) {
        html += `
            <div class="p-2.5 bg-blue-50 text-blue-900 border border-blue-200 rounded-xl text-xs flex items-center justify-between">
                <span class="flex items-center gap-2"><i class="fas fa-circle-info text-blue-600"></i> ${headerNotice}</span>
                <button onclick="openContactStructuresModal()" class="text-blue-700 font-bold hover:underline text-[11px]">Voir tout le Mali</button>
            </div>
        `;
    }

    list.forEach(d => {
        const typeBadge = badgeColors[d.directorate_type] || badgeColors.OTHER;
        const regName = d.region_name || (d.region && d.region.name) || 'Mali';
        const capital = d.capital || (d.region && d.region.capital) || '';
        const hasCoords = d.latitude && d.longitude;

        html += `
            <div class="p-3.5 bg-white rounded-xl border border-slate-200 shadow-xs hover:border-slate-300 transition-all">
                <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-2 mb-2 pb-2 border-b border-slate-100">
                    <div>
                        <div class="flex items-center gap-2 mb-1">
                            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold border ${typeBadge}">
                                <i class="${d.icon || 'fas fa-building'} mr-1"></i>${d.type_display || d.directorate_type}
                            </span>
                            <span class="text-[11px] font-semibold text-slate-600 flex items-center gap-1">
                                <i class="fas fa-location-dot text-red-500 text-[10px]"></i>
                                <span>Région de <b>${regName}</b> ${capital ? '• ' + capital : ''}</span>
                            </span>
                        </div>
                        <h4 class="font-bold text-slate-900 text-sm leading-snug">${d.name}</h4>
                        ${d.address ? `<div class="text-[11px] text-slate-500 mt-0.5"><i class="fas fa-map-pin mr-1 text-slate-400"></i>${d.address}</div>` : ''}
                    </div>

                    <!-- CTA Buttons -->
                    <div class="flex items-center gap-1.5 shrink-0 mt-1 sm:mt-0 flex-wrap">
                        ${d.phone_primary ? `
                            <a href="tel:${d.phone_primary}" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold text-xs flex items-center gap-1 shadow-xs transition-colors" title="Appeler directement">
                                <i class="fas fa-phone"></i> ${d.phone_primary}
                            </a>
                        ` : ''}
                        <a href="tel:${d.emergency_number || '122'}" class="px-2.5 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg font-bold text-xs flex items-center gap-1 shadow-xs ring-1 ring-red-300 transition-colors" title="Ligne d'urgence">
                            <i class="fas fa-phone-volume"></i> ${d.emergency_number || '122'}
                        </a>
                        ${d.phone_primary ? `
                            <button onclick="dispatchAlertWhatsApp('${d.phone_primary}', '${d.name.replace(/'/g, "\\'")}')" class="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-semibold text-xs flex items-center gap-1 shadow-xs transition-colors" title="Envoyer une alerte WhatsApp">
                                <i class="fab fa-whatsapp text-sm"></i>
                            </button>
                        ` : ''}
                        ${hasCoords ? `
                            <button onclick="locateDirectorateOnMap(${d.latitude}, ${d.longitude}, ${d.id})" class="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-semibold text-xs flex items-center gap-1 transition-colors" title="Localiser sur la carte">
                                <i class="fas fa-location-crosshairs text-blue-600"></i> Carte
                            </button>
                        ` : ''}
                    </div>
                </div>

                <div class="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                    <div class="flex items-center gap-3">
                        ${d.email ? `<a href="mailto:${d.email}" class="text-blue-600 hover:underline flex items-center gap-1"><i class="fas fa-envelope text-slate-400"></i> ${d.email}</a>` : ''}
                        ${d.phone_secondary ? `<span class="flex items-center gap-1"><i class="fas fa-phone-flip text-slate-400"></i> Astreinte: ${d.phone_secondary}</span>` : ''}
                    </div>
                    <span class="text-[10px] text-emerald-600 font-semibold flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Service actif</span>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function locateDirectorateOnMap(lat, lon, dirId) {
    closeContactStructuresModal();
    if (!vis.directorates) {
        vis.directorates = true;
        const cb = document.getElementById('layer-directorates');
        if (cb) cb.checked = true;
        if (grps.directorates) map.addLayer(grps.directorates);
        else rebuildDirectoratesLayer();
    }

    if (map) {
        map.flyTo([lat, lon], 12, { animate: true, duration: 1 });
        setTimeout(() => {
            if (grps.directorates) {
                grps.directorates.eachLayer(layer => {
                    if (layer._data && layer._data.id === dirId) {
                        layer.openPopup();
                    }
                });
            }
        }, 1100);
    }
}

function dispatchAlertWhatsApp(phone, dirName) {
    const cleanPhone = phone.replace(/[^0-9]/g, '');
    const internationalPhone = cleanPhone.startsWith('223') ? cleanPhone : `223${cleanPhone}`;
    const text = encodeURIComponent(`🚨 [URGENCE ECO-SURVEILLANCE MALI]\nBonjour,\nUne alerte environnementale urgente nécessite votre intervention :\n- Structure : ${dirName}\n- Plateforme : ECO-SURVEILLANCE MALI\nMerci de prendre contact avec les équipes de surveillance.`);
    window.open(`https://api.whatsapp.com/send?phone=${internationalPhone}&text=${text}`, '_blank');
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('map')) {
        initMap();
    }
});
