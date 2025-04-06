import streamlit as st
import time
import random # To simulate potential failures

# --- Placeholder WhatsApp Functionality ---

def initialize_whatsapp_client():
    """
    Placeholder for initializing the WhatsApp client using credentials
    from st.secrets (e.g., Twilio client, Meta API setup).
    Returns a dummy client object or None if 'configured'.
    """
    # In a real scenario, you'd load credentials here
    # Example:
    # try:
    #     account_sid = st.secrets["twilio"]["account_sid"]
    #     auth_token = st.secrets["twilio"]["auth_token"]
    #     # Initialize real client
    #     # client = Client(account_sid, auth_token)
    #     st.info("WhatsApp Client Initialized (Placeholder)")
    #     return "dummy_client" # Return a dummy object
    # except KeyError:
    #     st.warning("WhatsApp credentials not found in secrets.toml. Sending disabled.")
    #     return None
    # except Exception as e:
    #     st.error(f"Failed to initialize WhatsApp client: {e}")
    #     return None

    # For now, assume it's always 'initialized' for UI building purposes
    st.info("WhatsApp Client Initialized (Placeholder - Not sending real messages)")
    return "dummy_client"


def send_whatsapp_message(client, recipient_phone, message_body, client_name="Cliente"):
    """
    Placeholder function to simulate sending a WhatsApp message.
    In a real implementation, this would make the API call to the provider.
    """
    if not client:
        st.error("WhatsApp client not initialized.")
        return False

    # Clean phone number (basic example)
    cleaned_phone = ''.join(filter(str.isdigit, str(recipient_phone)))
    if not cleaned_phone:
        st.warning(f"Número de teléfono inválido para {client_name}: '{recipient_phone}'. Mensaje no enviado.")
        return False

    # --- Real API Call Would Go Here ---
    # Example (Twilio):
    # try:
    #     message = client.messages.create(
    #         from_='whatsapp:+YOUR_TWILIO_WHATSAPP_NUMBER',
    #         body=message_body,
    #         to=f'whatsapp:+{cleaned_phone}'
    #     )
    #     st.success(f"Mensaje enviado a {client_name} ({cleaned_phone}). SID: {message.sid}")
    #     return True
    # except Exception as e:
    #     st.error(f"Error al enviar mensaje a {client_name} ({cleaned_phone}): {e}")
    #     return False
    # ------------------------------------

    # Simulate sending delay and potential random failure
    st.info(f"Simulando envío a {client_name} ({cleaned_phone})...")
    time.sleep(random.uniform(0.5, 1.5)) # Simulate network delay
    
    # Simulate a 10% chance of failure for demonstration
    if random.random() < 0.1: 
        st.error(f"Simulación fallida: No se pudo enviar mensaje a {client_name} ({cleaned_phone}).")
        return False
    else:
        st.success(f"Simulación exitosa: Mensaje 'enviado' a {client_name} ({cleaned_phone}).")
        return True

def format_message(template, client_data):
    """
    Replaces placeholders in the template with client data.
    Placeholders should be like {Nombre_Apellido}, {Numero_Identificacion}, etc.
    """
    try:
        # Use dictionary comprehension for cleaner replacement
        # Ensure all keys exist in client_data, replace with '' if not
        formatted = template.format(**{key: client_data.get(key, '') for key in client_data})
        return formatted
    except KeyError as e:
        st.warning(f"Plantilla contiene una clave no encontrada en los datos del cliente: {e}. Se usará valor vacío.")
        # Attempt to format anyway, missing keys might be handled by .format depending on python version
        try:
             # Create a defaultdict-like behavior for missing keys
             class SafeDict(dict):
                 def __missing__(self, key):
                     return ''
             formatted = template.format_map(SafeDict(client_data))
             return formatted
        except Exception as format_e:
             st.error(f"Error al formatear plantilla: {format_e}")
             return template # Return original template on error
    except Exception as e:
        st.error(f"Error inesperado al formatear plantilla: {e}")
        return template # Return original template on error
