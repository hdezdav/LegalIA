#!/usr/bin/env python3
"""
Scraper oficial para Constitución Política de Colombia 1991.

Fuente: https://www.constitucioncolombia.com/
Estructura: 13 Títulos + Título Final + Disposiciones Transitorias

Este scraper extrae ÚNICAMENTE desde fuentes oficiales del Estado colombiano.
"""

import asyncio
import json
from pathlib import Path
from typing import List, Dict
import httpx
from bs4 import BeautifulSoup

# Estructura oficial de la Constitución de 1991
TITULOS = [
    {"numero": 1, "nombre": "De los principios fundamentales", "articulos": list(range(1, 11))},
    {"numero": 2, "nombre": "De los derechos, las garantías y los deberes", "capitulos": 5},
    {"numero": 3, "nombre": "De los habitantes y del territorio", "capitulos": 7},
    {"numero": 4, "nombre": "De la participación democrática y de los partidos políticos", "capitulos": 2},
    {"numero": 5, "nombre": "De la organización del Estado", "capitulos": 8},
    {"numero": 6, "nombre": "De la rama legislativa", "capitulos": 6},
    {"numero": 7, "nombre": "De la rama ejecutiva", "capitulos": 7},
    {"numero": 8, "nombre": "De la rama judicial", "capitulos": 7},
    {"numero": 9, "nombre": "De las elecciones y de la organización electoral", "capitulos": 2},
    {"numero": 10, "nombre": "De los organismos de control", "capitulos": 3},
    {"numero": 11, "nombre": "De la organización territorial", "capitulos": 3},
    {"numero": 12, "nombre": "Del régimen económico y de la hacienda pública", "capitulos": 5},
    {"numero": 13, "nombre": "De la reforma de la Constitución", "capitulos": 1},
]

BASE_URL = "https://www.constitucioncolombia.com"

async def fetch_articulos_titulo(client: httpx.AsyncClient, titulo_num: int) -> List[Dict]:
    """Extrae todos los artículos de un título."""
    url = f"{BASE_URL}/titulo-{titulo_num}"

    try:
        response = await client.get(url, timeout=30.0)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        articulos = []

        # Buscar títulos h3 que contienen los enlaces a artículos
        h3_elements = soup.find_all('h3')

        for h3 in h3_elements:
            a_elem = h3.find('a')
            if not a_elem:
                continue

            numero = a_elem.get_text(strip=True)
            if not ("Artículo" in numero or "Articulo" in numero or "Art" in numero):
                continue

            # El texto del artículo viene en el div con class="texto" siguiente
            texto_div = h3.find_next_sibling('div', class_='texto')
            if texto_div:
                texto = texto_div.get_text(strip=True)
                articulos.append({
                    'numero': numero,
                    'texto': texto,
                    'titulo': titulo_num
                })

        return articulos

    except Exception as e:
        print(f"⚠️  Error extrayendo Título {titulo_num}: {e}")
        return []



async def scrape_constitucion_completa() -> Dict:
    """Extrae la Constitución completa desde constitucioncolombia.com"""

    print("🏛️  Iniciando extracción de Constitución Política de Colombia 1991")
    print(f"📍 Fuente oficial: {BASE_URL}")
    print()

    constitucion = {
        'metadata': {
            'nombre': 'Constitución Política de Colombia',
            'año': 1991,
            'fuente_url': BASE_URL,
            'fuente_oficial': True,
            'entidad': 'República de Colombia',
            'tipo': 'CONSTITUCION',
            'status': 'VIGENTE'
        },
        'titulos': []
    }

    async with httpx.AsyncClient() as client:
        for titulo_info in TITULOS:
            titulo_num = titulo_info['numero']
            titulo_nombre = titulo_info['nombre']

            print(f"📖 Extrayendo Título {titulo_num}: {titulo_nombre}...")

            articulos = await fetch_articulos_titulo(client, titulo_num)

            if articulos:
                constitucion['titulos'].append({
                    'numero': titulo_num,
                    'nombre': titulo_nombre,
                    'articulos': articulos,
                    'total_articulos': len(articulos)
                })
                print(f"   ✅ {len(articulos)} artículos extraídos")
            else:
                print("   ⚠️  No se encontraron artículos")

            # Rate limiting - ser respetuosos con el servidor oficial
            await asyncio.sleep(1.5)

    return constitucion


async def main():
    """Extrae y guarda la Constitución completa."""

    output_dir = Path("/Users/law/Documents/GitHub/LegalIA/corpus/oficial")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extraer constitución
    constitucion = await scrape_constitucion_completa()

    # Contar artículos totales
    total_articulos = sum(t['total_articulos'] for t in constitucion['titulos'])

    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("✅ EXTRACCIÓN COMPLETADA")
    print(f"📊 Total artículos extraídos: {total_articulos}")
    print(f"📊 Total títulos procesados: {len(constitucion['titulos'])}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    # Guardar JSON estructurado
    json_path = output_dir / "constitucion_1991.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(constitucion, f, ensure_ascii=False, indent=2)

    print(f"💾 Guardado JSON: {json_path}")

    # Guardar texto plano para ingesta
    txt_path = output_dir / "constitucion_1991.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("CONSTITUCIÓN POLÍTICA DE COLOMBIA 1991\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Fuente oficial: {BASE_URL}\n")
        f.write("Entidad: República de Colombia\n")
        f.write("Estado: VIGENTE\n\n")

        for titulo in constitucion['titulos']:
            f.write(f"\nTÍTULO {titulo['numero']}\n")
            f.write(f"{titulo['nombre'].upper()}\n")
            f.write("=" * 80 + "\n\n")

            for articulo in titulo['articulos']:
                f.write(f"{articulo['numero']}\n")
                f.write(f"{articulo['texto']}\n\n")

    print(f"💾 Guardado TXT: {txt_path}")
    print()
    print("✅ Listo para ingestar con:")
    print(f"   python -m ingestion.main --file {txt_path} --status VIGENTE")


if __name__ == "__main__":
    asyncio.run(main())
