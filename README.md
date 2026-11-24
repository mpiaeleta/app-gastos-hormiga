# 🐜 App de gastos hormiga y costo de oportunidad (Streamlit)

Cada persona carga sus gastos (archivo CSV/Excel o a mano) y la app calcula:
1. cuánto tendría hoy si ese dinero se hubiera invertido en plazo fijo, FCI, dólar o bitcoin (contra la inflación);
2. cuánto tendría en N meses si ahorrara su gasto hormiga de ahora en adelante, y cuánto necesita para ganarle a la inflación;
3. un resumen en lenguaje simple (con IA si hay clave de Claude; si no, con una plantilla).

Los datos de mercado (inflación, plazo fijo, FCI, dólar y bitcoin) se descargan **en vivo** y se guardan en caché 6 horas.

## Archivos
| Archivo | Qué hace |
|---|---|
| `app.py` | La pantalla (Streamlit) |
| `core.py` | Toda la lógica: datos, clasificación, costo de oportunidad, proyección, IA |
| `graficos.py` | Los gráficos |
| `requirements.txt` | Librerías |

## Opción A — correrla en tu computadora
1. Instalá Python 3.10 o más nuevo.
2. En la carpeta de la app: `pip install -r requirements.txt`
3. `streamlit run app.py` → se abre en el navegador (http://localhost:8501).

## Opción B — publicarla con un link (Streamlit Community Cloud, gratis)
1. Creá un repositorio en GitHub y subí los 4 archivos de arriba.
2. Entrá a https://share.streamlit.io, iniciá sesión con GitHub y elegí **Create app**.
3. Elegí tu repositorio, rama `main` y archivo `app.py` → **Deploy**.
4. Cuando termine, tenés un link público para compartir.

## IA (opcional)
Sin clave, todo funciona: el resumen sale por plantilla y las categorías por palabras clave.
Para activar la IA (Claude): en la barra lateral pegá tu clave, o en Streamlit Cloud cargala en
**Settings → Secrets** como `ANTHROPIC_API_KEY = "tu-clave"`. A la IA solo se envían las
descripciones sin clasificar (sin montos ni fechas) y cifras agregadas para el resumen.

## Notas
- Los gastos viven solo en la sesión del navegador: usá **Descargar mis gastos** para guardarlos.
- Es un ejercicio ilustrativo, no una recomendación de inversión.
