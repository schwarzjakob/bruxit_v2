from src.utils.utils import parse_data_structure, sort_data_structure
from src.services.settings_service import get_settings


def list_patient_data():
    original_data_path = get_settings().original_data_path
    result = parse_data_structure(original_data_path)
    return sort_data_structure(result)
