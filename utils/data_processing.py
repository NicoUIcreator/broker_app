import pandas as pd
import streamlit as st
from io import BytesIO # Para leer archivos subidos en memoria

  # Importar encabezados desde el módulo de sheets para consistencia
from .google_sheets import ENCABEZADOS 

def leer_excel_subido(uploaded_file):
      """Lee un archivo Excel subido vía Streamlit y lo devuelve como DataFrame."""
      try:
          # Usar BytesIO para que pandas pueda leer el objeto UploadedFile
          bytes_data = uploaded_file.getvalue()
          # Intentar con openpyxl primero (xlsx)
          try:
              df = pd.read_excel(BytesIO(bytes_data), engine='openpyxl')
              st.info(f"Archivo '{uploaded_file.name}' leído correctamente (xlsx).")
              return df
          except Exception as e_xlsx:
              st.warning(f"No se pudo leer '{uploaded_file.name}' como xlsx ({e_xlsx}), intentando como xls...")
              # Si falla, intentar con el motor por defecto (puede usar xlrd si está instalado)
              try:
                  df = pd.read_excel(BytesIO(bytes_data))
                  st.info(f"Archivo '{uploaded_file.name}' leído correctamente (xls/otro).")
                  return df
              except Exception as e_xls:
                  st.error(f"Error al leer el archivo Excel '{uploaded_file.name}' con ambos motores: {e_xls}")
                  return None
      except Exception as e:
          st.error(f"Error general al procesar el archivo subido '{uploaded_file.name}': {e}")
          return None

def preparar_datos_para_hoja(df_compania, nombre_compania):
      """
      Procesa el DataFrame de la compañía para adaptarlo a la estructura estándar.
      *** ESTA ES LA PARTE MÁS IMPORTANTE A PERSONALIZAR POR COMPAÑÍA ***
      Devuelve una lista de listas, donde cada lista interna es una fila.
      """
      datos_procesados = []
      progreso = st.progress(0)
      total_filas = len(df_compania)
      
      st.write(f"Procesando {total_filas} filas para {nombre_compania}...")

      # --- ¡¡¡PERSONALIZACIÓN CRÍTICA AQUÍ!!! ---
      # Detectar estructura basada en nombre_compania o columnas presentes
      # EJEMPLO MUY BÁSICO - DEBES ADAPTARLO A TUS EXCEL REALES
      
      columnas_df = df_compania.columns.str.lower().tolist() # Nombres de columna en minúsculas
      
      # Mapeo de columnas esperado (ejemplos, ¡ajústalos!)
      map_dni = 'dni' if 'dni' in columnas_df else 'dni_cliente' if 'dni_cliente' in columnas_df else None
      map_nombre = 'nombre' if 'nombre' in columnas_df else 'nombre completo' if 'nombre completo' in columnas_df else 'apellido y nombre' if 'apellido y nombre' in columnas_df else None
      map_tel = 'telefono' if 'telefono' in columnas_df else 'tel' if 'tel' in columnas_df else 'celular' if 'celular' in columnas_df else None
      map_id_comp = 'id_cliente' if 'id_cliente' in columnas_df else 'nro cliente' if 'nro cliente' in columnas_df else None
      map_email = 'email' if 'email' in columnas_df else 'correo' if 'correo' in columnas_df else None
      map_tipo_id = 'tipo doc' if 'tipo doc' in columnas_df else None # Si tienes esta info
      
      # Validar que las columnas mínimas existan
      if not map_dni or not map_nombre:
           st.error(f"¡Error crítico! No se encontraron columnas de DNI o Nombre en el Excel de {nombre_compania}. Columnas encontradas: {columnas_df}")
           return [] # Devolver vacío si no hay datos esenciales

      for index, row in df_compania.iterrows():
          try:
              # Extraer datos usando los mapeos (con manejo de nulos)
              num_id = str(row[map_dni]) if map_dni and pd.notna(row[map_dni]) else ''
              nombre = str(row[map_nombre]) if map_nombre and pd.notna(row[map_nombre]) else ''
              telefono1 = str(row[map_tel]) if map_tel and pd.notna(row[map_tel]) else ''
              id_cliente_compania = str(row[map_id_comp]) if map_id_comp and pd.notna(row[map_id_comp]) else ''
              email = str(row[map_email]) if map_email and pd.notna(row[map_email]) else ''
              tipo_id = str(row[map_tipo_id]) if map_tipo_id and pd.notna(row[map_tipo_id]) else 'DNI' # Valor por defecto
              
              # Limpieza básica (ejemplo)
              num_id = num_id.replace('.', '').replace('-', '').strip()
              telefono1 = ''.join(filter(str.isdigit, telefono1)) # Dejar solo dígitos en teléfono

              # Validar datos mínimos
              if not num_id or not nombre:
                  st.warning(f"Fila {index+2} omitida por falta de DNI o Nombre.")
                  continue

              # --- Crear la fila con la estructura estándar ---
              fila_nueva = [
                  '',             # ID_Cliente_Unico (se podría generar aquí o en Sheets)
                  nombre,
                  num_id,
                  tipo_id,
                  telefono1,
                  '',             # Numero_Telefono_2 (buscar si hay otra columna de tel)
                  email,
                  id_cliente_compania,
                  pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'), # Fecha_Ultima_Actualizacion
                  'FALSE',        # Mensaje_WSP_Enviado (valor inicial)
                  ''              # Notas
              ]
              
              if len(fila_nueva) == len(ENCABEZADOS):
                  datos_procesados.append(fila_nueva)
              else:
                   st.warning(f"Advertencia: Fila {index+2} de {nombre_compania} generó {len(fila_nueva)} columnas, se esperaban {len(ENCABEZADOS)}. Fila omitida.")

          except KeyError as e:
              st.warning(f"Advertencia: Falta columna esperada {e} en fila {index+2} de {nombre_compania}. Fila omitida.")
          except Exception as e:
              st.error(f"Error procesando fila {index+2} de {nombre_compania}: {e}. Fila omitida.")
          
          # Actualizar barra de progreso
          progreso.progress((index + 1) / total_filas)

      st.success(f"Se prepararon {len(datos_procesados)} registros válidos de {nombre_compania}.")
      return datos_procesados