from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ProjectStage(StrEnum):
    CONCEPT = "Concept"
    COMPONENT_SELECTION = "Component selection"
    PROCUREMENT = "Procurement"
    INTEGRATION = "Integration"
    TESTING = "Testing"
    COMPLETED = "Completed"


class OperatingEnvironment(StrEnum):
    INDOOR = "Indoor"
    OUTDOOR = "Outdoor"
    MIXED = "Mixed"
    LAB = "Controlled laboratory"
    UNKNOWN = "Unknown"


class RiskTolerance(StrEnum):
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"


class Requiredness(StrEnum):
    MANDATORY = "Mandatory"
    CONDITIONAL = "Conditional"
    OPTIONAL = "Optional"
    EXPERIMENTAL = "Experimental"
    DEFERRED = "Deferred"


class RoleRequiredness(StrEnum):
    MANDATORY = "Mandatory"
    CONDITIONAL = "Conditional"
    OPTIONAL = "Optional"
    EXPERIMENTAL = "Experimental"
    DEFERRED = "Deferred"
    REMOVED = "Removed"


class RoleStatus(StrEnum):
    PROPOSED = "Proposed"
    CANDIDATE = "Candidate identified"
    SELECTED = "Selected"
    ORDERED = "Ordered"
    RECEIVED = "Received"
    INSPECTED = "Inspected"
    VERIFIED = "Verified individually"
    INTEGRATED = "Integrated"
    SYSTEM_TESTED = "System tested"
    REMOVED = "Removed"


class RelationshipType(StrEnum):
    REQUIRES = "Requires"
    REQUIRES_COMPATIBLE = "Requires compatible"
    ENABLES = "Enables"
    POWERED_BY = "Powered by"
    CONNECTS_TO = "Connects to"
    ALTERNATIVE_TO = "Alternative to"
    COMPATIBLE_WITH = "Compatible with"
    INCOMPATIBLE_WITH = "Incompatible with"
    OPTIONAL_FOR = "Optional for"
    REQUIRED_FOR = "Required for"


class Strength(StrEnum):
    HARD = "Hard"
    SOFT = "Soft"
    ADVISORY = "Advisory"


class RelationshipValidationStatus(StrEnum):
    UNVERIFIED = "Unverified"
    USER_CONFIRMED = "User confirmed"
    SPEC_CONFIRMED = "Specification confirmed"
    TESTED = "Tested"
    FAILED = "Failed"


class LogicType(StrEnum):
    ALL_OF = "ALL_OF"
    ANY_OF = "ANY_OF"
    N_OF_M = "N_OF_M"


class RequirementStrength(StrEnum):
    HARD = "Hard"
    SOFT = "Soft"


class SelectionStatus(StrEnum):
    CANDIDATE = "Candidate"
    PREFERRED = "Preferred"
    SELECTED = "Selected"
    REJECTED = "Rejected"


class PurchaseStatus(StrEnum):
    NOT_PLANNED = "Not planned"
    PLANNED = "Planned"
    ORDERED = "Ordered"
    RECEIVED = "Received"
    RETURNED = "Returned"


class VerificationStatus(StrEnum):
    UNVERIFIED = "Unverified"
    SPEC_REVIEWED = "Specification reviewed"
    BENCH_TESTED = "Bench tested"
    INTEGRATED = "Integrated"
    FAILED = "Failed"


class FindingSeverity(StrEnum):
    BLOCKING = "Blocking error"
    WARNING = "Warning"
    INFORMATIONAL = "Informational"


class EntityType(StrEnum):
    CAPABILITY = "Capability"
    COMPONENT_ROLE = "Component role"
    MILESTONE = "Milestone"
    PRODUCT = "Specific product"


class ReadinessStatus(StrEnum):
    READY = "Ready"
    AT_RISK = "At risk"
    BLOCKED = "Blocked"
    INCOMPLETE = "Incomplete"
    NOT_EVALUATED = "Not evaluated"
    COMPLETED = "Completed"
