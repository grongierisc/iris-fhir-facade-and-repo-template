from fhir_validator import FhirValidator

PROFILES = ["hl7.fhir.fr.core@2.1.0"]

_validator = None


def _get_validator() -> FhirValidator:
    global _validator
    if _validator is None:
        _validator = (
            FhirValidator.create(fhir_version="R4")
            .add_package("hl7.fhir.fr.core@2.1.0")
            .with_unknown_code_system_mode("warning")
        )
    return _validator


def is_valid_fhir(payload: dict) -> tuple[bool, dict]:
    result = _get_validator().validate(payload)
    return result.is_valid(), result.to_fhir()