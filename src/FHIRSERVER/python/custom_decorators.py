"""
FHIR Server Customization using Decorators.

This module demonstrates how to use decorators to customize FHIR server behavior.
Simply import fhir and decorate your functions.
"""

import json
import threading
from typing import Any, Dict, List, Optional

from iris_fhir_python_strategy import fhir,dynamic_object_from_json, get_interactions_context, get_request_context, RequestContext
from fhir_validator import FhirValidator

ictx = get_interactions_context()
ictx.validator = (
            FhirValidator.create(fhir_version="R4")
            .add_package("hl7.fhir.fr.core@2.1.0")
            .with_unknown_code_system_mode("warning")
        )

# ==================== Capability Statement ====================

@fhir.on_capability_statement
def customize_capability_statement(capability_statement: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove Account resource from capability statement.
    """
    capability_statement['rest'][0]['resource'] = [
        resource for resource in capability_statement['rest'][0]['resource'] 
        if resource['type'] != 'Account'
    ]
    return capability_statement


# ==================== Request/Response Hooks ====================

@fhir.on_before_request
def extract_user_context(fhir_service: Any, fhir_request: Any, body: Dict[str, Any], timeout: int):
    """
    Extract user and roles for consent evaluation.
    """
    ctx = RequestContext()
    ctx.username = fhir_request.Username
    ctx.roles = fhir_request.Roles
    ctx.interactions = fhir_service.interactions
    ctx.scope_list = []
    ctx.security_list = ["VIP"]  # Example: Assume all users don't have VIP access for testing

@fhir.on_after_request
def cleanup_context(fhir_service: Any, fhir_request: Any, fhir_response: Any, body: Dict[str, Any]):
    """
    Clear request-scoped state.
    """
    pass


# ==================== Read/Search Processing ====================

@fhir.on_after_read("Patient")
def filter_patient_read(fhir_object: Dict[str, Any]) -> bool:
    """
    Apply consent rules to Patient reads.
    Return False to hide the resource (returns 404).
    """
    # Uncomment to enable consent checking
    # return check_consent(fhir_object)
    return True


@fhir.on_after_read()  # All resource types
def log_all_reads(fhir_object: Dict[str, Any]) -> bool:
    """
    Log all read operations.
    """
    print(f"Reading {fhir_object.get('resourceType')} with ID {fhir_object.get('id')}")
    return True


@fhir.on_after_search("Patient")
def filter_patient_search(rs: Any, resource_type: str):
    """
    Filter Patient search results based on consent.
    """
    ctx = get_request_context()
    rs._SetIterator(0)
    while rs._Next():
        resource_id = rs._Get("ResourceId")
        version_id = rs._Get("VersionId")
        json_str = ctx.interactions.Read(resource_type, resource_id, version_id)._ToJSON()
        resource_dict = json.loads(json_str)
        if not check_consent(resource_dict):
            rs.MarkAsDeleted()
            rs._SaveRow()


# ==================== Consent Rules ====================

@fhir.consent("Patient")
def patient_consent_rules(fhir_object: Dict[str, Any], user_context: Any) -> bool:
    """
    Check if user has consent to access Patient resource.
    """
    return check_consent(fhir_object)


# ==================== CRUD Operations ====================

@fhir.on_before_create("Patient")
def validate_patient_creation(fhir_service: Any, fhir_request: Any, body: Dict[str, Any], timeout: int):
    """
    Validate Patient resource before creation.
    """
    # Add custom validation logic here
    pass


@fhir.on_before_update("Patient")
def audit_patient_update(fhir_service: Any, fhir_request: Any, body: Dict[str, Any], timeout: int):
    """
    Audit Patient updates.
    """
    # Log patient updates for compliance
    pass


# ==================== Custom Operations ====================

@fhir.operation("diff", scope="Instance", resource_type="Patient")
def patient_diff_operation(operation_name: str, operation_scope: str, body: Dict[str, Any],
                          fhir_service: Any, fhir_request: Any, fhir_response: Any):
    """
    Custom $diff operation to compare two Patient resources.
    """
    from deepdiff import DeepDiff

    # Get the primary resource
    primary_resource = json.loads(
        fhir_service.interactions.Read(
            fhir_request.Type, 
            fhir_request.Id
        )._ToJSON()
    )
    
    # Get the secondary resource from request body
    secondary_resource = json.loads(fhir_request.Json._ToJSON())
    
    # Calculate diff using deepdiff
    diff = DeepDiff(primary_resource, secondary_resource, ignore_order=True).to_json()
    
    # Create response
    fhir_response.Json = dynamic_object_from_json(diff)
    
    return fhir_response


@fhir.operation("validate", scope="Type", resource_type="Patient")
def validate_patient_operation(operation_name: str, operation_scope: str, body: Dict[str, Any],
                               fhir_service: Any, fhir_request: Any, fhir_response: Any):
    """
    Custom $validate operation for Patient resources.
    """
    # Use FhirValidateOperation for validation
    ictx = get_interactions_context()
    validation_result = ictx.validator.validate(body)
    fhir_response.Json = validation_result


# ==================== Helper Functions ====================


def check_consent(resource_dict: Dict[str, Any]) -> bool:
    """
    Check if user has consent to access resource.
    Returns False if access should be denied.
    """
    ctx = get_request_context()
    if "meta" in resource_dict:
        if "security" in resource_dict["meta"]:
            for security in resource_dict["meta"]["security"]:
                if security.get("code") in ctx.security_list:
                    return False
    return True


# ==================== Validation Decorators ====================

@fhir.on_validate_resource() # Applies to all resource types (before any other validation)
def validate_resource_schema(resource_object: Dict[str, Any], is_in_transaction: bool = False):
    """
    Validate resource against FHIR schema.
    Raises exception if validation fails.
    """
    ictx = get_interactions_context()
    validation_result = ictx.validator.validate(resource_object)
    return validation_result.to_fhir()  # Return validation result as FHIR OperationOutcome

@fhir.on_validate_resource("*")
def generic_resource_validation(resource_object: Dict[str, Any], is_in_transaction: bool = False):
    """
    Generic resource validation for all resource types.
    Raises exception if validation fails.
    """
    # Example: Ensure resource has an ID
    if "id" not in resource_object:
        raise ValueError("Resource must have an 'id' field")


@fhir.on_validate_resource("Observation")
def validate_observation_resource(resource_object, is_in_transaction=False):
    """
    Custom validation for Observation resources.
    """
    # Example: Ensure critical observations have comments
    if "code" in resource_object:
        coding = resource_object["code"].get("coding", [])
        for code in coding:
            if code.get("code") in ["critical-001", "critical-002"]:
                if "note" not in resource_object:
                    raise ValueError("Critical observations must include a note")

