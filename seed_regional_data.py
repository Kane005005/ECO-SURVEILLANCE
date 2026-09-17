#!/usr/bin/env python
"""
ECO-SURVEILLANCE MALI — Script de Seed des 19 Régions Administratives (Loi 2023)
et des Directions Régionales Opérationnelles (DRPC, DRH, DREF, DRACPN, DRA).

Usage direct :
    python seed_regional_data.py
Ou via commande Django :
    python manage.py seed_mali_regions_and_directorates
"""
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()

    from django.core.management import call_command
    print("Execution du seed des regions et directions regionales...")
    call_command("seed_mali_regions_and_directorates")
    print("Seed termine avec succes !")
