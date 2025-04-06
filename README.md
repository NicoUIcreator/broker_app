# Gestor de Clientes Broker - Streamlit App

Esta es una aplicación web desarrollada con Streamlit diseñada para ayudar a gestionar la información de clientes, utilizando Google Sheets como backend para el almacenamiento de datos.

## Funcionalidades Principales

1.  **Inicio de Sesión Seguro:** Acceso a la aplicación mediante credenciales de usuario y contraseña definidas en el archivo `.streamlit/secrets.toml`.
2.  **Carga de Datos desde Excel:**
    *   Permite subir archivos Excel (`.xlsx`, `.xls`) con información de clientes.
    *   El usuario asigna un nombre de "Compañía" a cada archivo subido, que se utilizará como nombre de la hoja en Google Sheets.
    *   El sistema procesa los datos del Excel, intentando mapear las columnas a una estructura estándar (ver `utils/data_processing.py` para la lógica de mapeo, **requiere personalización**).
3.  **Integración con Google Sheets:**
    *   Se conecta a una hoja de cálculo específica de Google Sheets (ID definido en `secrets.toml`).
    *   Utiliza credenciales de cuenta de servicio de Google Cloud (configuradas en `secrets.toml` o localmente en `credentials.json`).
    *   Verifica si existe una hoja para la compañía; si no, la crea automáticamente con encabezados predefinidos.
    *   **Agrega o Actualiza Datos:** Compara los datos del Excel con los existentes en la hoja basándose en el `Numero_Identificacion`. Agrega clientes nuevos y actualiza los existentes, conservando el ID único y el estado del mensaje WhatsApp.
4.  **Visualización y Gestión de Clientes:**
    *   Permite seleccionar una compañía (hoja) para ver sus clientes.
    *   Muestra los datos en una tabla interactiva.
    *   Ofrece filtros por nombre/apellido y por estado de envío de WhatsApp (`Mensaje_WSP_Enviado`).
    *   Permite marcar individualmente a los clientes como "Mensaje Enviado" (TRUE) o "Pendiente" (FALSE), actualizando la hoja de Google Sheets.
5.  **Envío de Mensajes (Próximamente):**
    *   Incluye una sección placeholder para una futura integración con API de WhatsApp para enviar mensajes masivos o individuales.

## Estructura del Proyecto

*   `app.py`: Archivo principal de la aplicación Streamlit. Contiene la interfaz de usuario y la lógica de navegación.
*   `utils/`: Carpeta con módulos auxiliares.
    *   `google_sheets.py`: Funciones para interactuar con la API de Google Sheets (autenticación, leer, escribir, actualizar, crear hojas). Define los `ENCABEZADOS` estándar.
    *   `data_processing.py`: Funciones para leer archivos Excel y transformar los datos a la estructura requerida por Google Sheets. **Contiene la lógica de mapeo de columnas que necesita ser adaptada a los formatos de Excel específicos.**
*   `.streamlit/secrets.toml`: Archivo de configuración para almacenar credenciales de login, ID de Google Sheet y credenciales de la API de Google (no incluido en el repositorio por seguridad).
*   `requirements.txt`: Lista de dependencias Python necesarias.
*   `README.md`: Este archivo.

## Configuración y Ejecución

1.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Configurar Secretos:**
    *   Crea un archivo `.streamlit/secrets.toml`.
    *   Añade las siguientes secciones y claves:
        ```toml
        # .streamlit/secrets.toml

        [login]
        username = "tu_usuario"
        password = "tu_contraseña"

        [google_sheets]
        spreadsheet_id = "ID_DE_TU_HOJA_DE_CALCULO_GOOGLE"

        # Credenciales de la cuenta de servicio de Google Cloud
        # (Obtenidas como archivo JSON desde Google Cloud Console)
        [google_credentials]
        type = "service_account"
        project_id = "tu-project-id"
        private_key_id = "tu-private-key-id"
        private_key = "-----BEGIN PRIVATE KEY-----\nTU_CLAVE_PRIVADA_AQUI\n-----END PRIVATE KEY-----\n"
        client_email = "tu-email-de-servicio@tu-project-id.iam.gserviceaccount.com"
        client_id = "tu-client-id"
        auth_uri = "https://accounts.google.com/o/oauth2/auth"
        token_uri = "https://oauth2.googleapis.com/token"
        auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
        client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/tu-email-de-servicio%40tu-project-id.iam.gserviceaccount.com"
        universe_domain = "googleapis.com"

        # Asegúrate de compartir tu Google Sheet con el client_email de la cuenta de servicio
        ```
    *   **Alternativa para Desarrollo Local:** Puedes colocar el archivo JSON de credenciales de Google Cloud como `credentials.json` en la raíz del proyecto. La aplicación intentará usar `secrets.toml` primero.
3.  **Personalizar Mapeo de Datos:**
    *   Edita la función `preparar_datos_para_hoja` en `utils/data_processing.py` para que coincida con las estructuras de columnas de tus archivos Excel.
4.  **Ejecutar la Aplicación:**
    ```bash
    streamlit run app.py
    ```

## Notas Importantes

*   La lógica de mapeo en `utils/data_processing.py` es crucial y debe adaptarse a los formatos específicos de los archivos Excel que se cargarán.
*   Asegúrate de que la cuenta de servicio de Google (`client_email`) tenga permisos de edición sobre la Google Sheet especificada.
