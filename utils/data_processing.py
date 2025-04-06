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
      
      # Convertimos a minúsculas y quitamos espacios/puntos para comparar
      columnas_normalizadas = [col.lower().replace(' ', '').replace('.', '') for col in df_compania.columns]
      
      # Mapeo de columnas esperado usando nombres normalizados
      map_dni = None
      colonna_reales = list(df_compania.columns)  
      
      # Buscar solo columna de nombre (único campo requerido)
      map_nombre = next((col for i, col in enumerate(colonna_reales) 
                       if ('nombre' in columnas_normalizadas[i] or 
                           'apellido' in columnas_normalizadas[i] or
                           'tomador' in columnas_normalizadas[i])), None)

      # Buscar teléfono usando nombres normalizados
      map_tel = next((col for i, col in enumerate(colonna_reales) 
                    if 'telefono' in columnas_normalizadas[i] or 
                       'tel' in columnas_normalizadas[i] or
                       'celular' in columnas_normalizadas[i] or
                       'movil' in columnas_normalizadas[i]), None)

      # Buscar ID de compañía usando nombres normalizados
      map_id_comp = next((col for i, col in enumerate(colonna_reales) 
                        if 'idcliente' in columnas_normalizadas[i] or
                           'nrocliente' in columnas_normalizadas[i] or
                           'poliza' in columnas_normalizadas[i] or
                           'contrato' in columnas_normalizadas[i]), None)

      # Buscar email usando nombres normalizados
      map_email = next((col for i, col in enumerate(colonna_reales) 
                      if 'email' in columnas_normalizadas[i] or
                         'correo' in columnas_normalizadas[i] or
                         'mail' in columnas_normalizadas[i]), None)

      # Buscar tipo de documento usando nombres normalizados
      map_tipo_id = next((col for i, col in enumerate(colonna_reales) 
                        if 'tipodoc' in columnas_normalizadas[i] or
                           'tipodocumento' in columnas_normalizadas[i] or
                           'documento' in columnas_normalizadas[i]), 'DNI') # Valor por defecto

      # Validar que la columna de nombre exista (único campo requerido)
      if not map_nombre:
           st.error(f"¡Error crítico! No se encontró columna de Nombre/Tomador en el Excel de {nombre_compania}. Columnas encontradas: {df_compania.columns.tolist()}")
           return [] # Devolver vacío si no hay nombre

      for index, row in df_compania.iterrows():
          try:
              # Extraer datos - generamos ID automático siempre usando prefijo de compañía
              num_id = f"ID_{nombre_compania[:3]}_{index}"
              nombre = str(row[map_nombre]) if map_nombre and pd.notna(row[map_nombre]) else ''
              telefono1 = str(row[map_tel]) if map_tel and pd.notna(row[map_tel]) else ''
              id_cliente_compania = str(row[map_id_comp]) if map_id_comp and pd.notna(row[map_id_comp]) else ''
              email = str(row[map_email]) if map_email and pd.notna(row[map_email]) else ''
              tipo_id = str(row[map_tipo_id]) if map_tipo_id and pd.notna(row[map_tipo_id]) else 'DNI' # Valor por defecto
              
              # Limpieza básica
              num_id = num_id.replace('.', '').replace('-', '').strip()
              telefono1 = ''.join(filter(str.isdigit, telefono1)) # Dejar solo dígitos en teléfono

              # Validar solo el nombre como campo requerido
              if not nombre:
                  st.warning(f"Fila {index+2} omitida por falta de nombre.")
                  continue

              # Si no hay ID, generamos uno basado en el índice
              if not num_id:
                  num_id = f"ID_{nombre_compania[:3]}_{index}"

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
