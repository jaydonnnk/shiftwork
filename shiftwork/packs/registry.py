"""Pure, immutable engagement declarations. Admission belongs to orchestration."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from shiftwork.domain.errors import ShiftworkDomainError
from shiftwork.domain.models import AssistRole

_FROZEN = ConfigDict(frozen=True, extra="forbid")
Text = Annotated[str, Field(min_length=1)]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
PackPath = Annotated[str, Field(pattern=r"^[a-zA-Z0-9_./-]+$")]


class PackNotFound(ShiftworkDomainError):
    kind = "not_found"


class PackUnavailable(ShiftworkDomainError):
    """A declaration or its reviewed material cannot be admitted."""


class FamilyClass(StrEnum):
    ATTEMPT = "ATTEMPT"
    COMPARISON = "COMPARISON"


class FamilyDeclaration(BaseModel):
    model_config = _FROZEN
    family: Text
    family_class: FamilyClass
    case_file: PackPath
    cycle: Annotated[int, Field(strict=True, ge=1)]
    min_variants: Annotated[int, Field(strict=True, ge=1)]

    @model_validator(mode="after")
    def comparison_minimum(self):
        if self.family_class is FamilyClass.COMPARISON and self.min_variants < 6:
            raise ValueError("a comparison family requires at least six variants")
        parts = self.case_file.split("/")
        if (len(parts) != 3 or parts[:2] != ["sealed", "cases"]
                or parts[2] in ("", ".", "..") or not parts[2].endswith(".json")):
            raise ValueError("a family must use the controller sealed storage")
        return self


class PackDocument(BaseModel):
    model_config = _FROZEN
    doc_id: Text
    path: PackPath
    sha256: Sha256
    station: Text


class ReviewedPin(BaseModel):
    model_config = _FROZEN
    path: PackPath
    sha256: Sha256


class AssistPolicy(BaseModel):
    model_config = _FROZEN
    level_label: Text
    allowed_roles: tuple[AssistRole, ...]
    total_calls_per_shift: Annotated[int, Field(strict=True, ge=0)]
    max_patch_proposals: Annotated[int, Field(strict=True, ge=0)]

    @model_validator(mode="after")
    def bounded_roles(self):
        if not self.allowed_roles or len(set(self.allowed_roles)) != len(self.allowed_roles):
            raise ValueError("assist roles must be non-empty and unique")
        if self.max_patch_proposals > self.total_calls_per_shift:
            raise ValueError("patch budget exceeds total assistance budget")
        if self.max_patch_proposals and AssistRole.PATCH_PROPOSAL not in self.allowed_roles:
            raise ValueError("patch budget requires the patch role")
        return self


class BoardDisplay(BaseModel):
    model_config = _FROZEN
    role_name: Text
    employer: Text | None
    client: Text | None
    room_id: Text
    station_labels: tuple[Text, ...]

    @model_validator(mode="after")
    def complete_display(self):
        if not (self.employer or self.client) or not self.station_labels:
            raise ValueError("a board needs its workplace and station labels")
        return self


class ConsequenceRules(BaseModel):
    model_config = _FROZEN
    success_events: tuple[Text, ...]
    rollout_event: Text | None
    handover_record_required: bool


class EngagementPack(BaseModel):
    model_config = _FROZEN
    slug: Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]*$")]
    schema_version: Literal[1]
    display: BoardDisplay
    assist: AssistPolicy
    mission_path: PackPath
    public_state_path: PackPath
    comparison_state_path: PackPath
    incident_request_path: PackPath
    manifest_path: PackPath
    documents: tuple[PackDocument, ...]
    families: tuple[FamilyDeclaration, ...]
    consequences: ConsequenceRules
    reviewed_pins: tuple[ReviewedPin, ...]

    @model_validator(mode="after")
    def coherent_declaration(self):
        if not any(f.family_class is FamilyClass.COMPARISON for f in self.families):
            raise ValueError("a pack requires a comparison family")
        for values, label in (
            ([f.family for f in self.families], "family name"),
            ([d.doc_id for d in self.documents], "document id"),
            ([p.path for p in self.reviewed_pins], "reviewed pin"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {label}")
        paths = (*self.required_paths(), *(pin.path for pin in self.reviewed_pins))
        if any(p.startswith("/") or any(part in ("", ".", "..") for part in p.split("/"))
               for p in paths):
            raise ValueError("pack paths must stay within the package")
        return self

    def required_paths(self) -> tuple[str, ...]:
        return (self.mission_path, self.public_state_path, self.comparison_state_path,
                self.incident_request_path, self.manifest_path,
                *(doc.path for doc in self.documents), *(f.case_file for f in self.families))


class BoardAvailability(BaseModel):
    model_config = _FROZEN
    engagement_slug: str
    display: BoardDisplay
    availability: Literal["AVAILABLE", "AWAITING_OPERATOR_REVIEW"]


# These literal pins preserve accepted, code-shipped Bellwether content. They
# are never calculated on lookup. Northline has separate approved pins below.
_BELLWETHER_PINS = (
    ReviewedPin(path="fixtures/mission/bookshop_pivot_v1.json", sha256="aebe89555a72688eedfb564088f57b78328c184d0a4e378918c46d13d1e6c12a"),
    ReviewedPin(path="fixtures/shop/bookshop_pivot_public_state.json", sha256="6bc17d69f43b24aa6048fdead7747e5820cd5740e47ba03a4a004d9ddea3c32c"),
    ReviewedPin(path="fixtures/shop/bookshop_compare_state_v1.json", sha256="4abe54462600ade9793c1d7dc32978c427d4f0b0a5e5b121830cfc3b478a2f6f"),
    ReviewedPin(path="fixtures/requests/bookshop_pivot_incident.jsonl", sha256="e9ae58c7d352f3f21b1f0edacbfcabf73a7c0edc0f551e7eb0bea8ae829cc399"),
    ReviewedPin(path="fixtures/requests/bookshop_compare_manifest.json", sha256="2391255db772f42577ad2676c16a39b85b5867923334155f5dd129e8f5930e3f"),
    ReviewedPin(path="fixtures/catalogs/bookshop_v3.json", sha256="80129ded2e63240bb30bb2d462dcc3a1a988d6f615a8209f3f891671c9a03f8d"),
    ReviewedPin(path="fixtures/artifacts/bookshop/pivot_starter_failure_service.py", sha256="0069462dd0e1946f296ccd5f4aefbade8d8c3cffa08c39bd3854954b27be36ef"),
    ReviewedPin(path="sealed/cases/bookshop_stale_information.json", sha256="de98240fdfe9c25c849de1d17116c6ec0bea6ab6c1048f7ab83ea06dca09a500"),
    ReviewedPin(path="sealed/cases/bookshop_policy_exception.json", sha256="fa6e258b82ddf6486de5203b1b1f5338e478cf0230422a12b46e9f3feb9ce59c"),
    ReviewedPin(path="sealed/cases/bookshop_hostile_instruction.json", sha256="2f4657dc239bbdcaf632ca08483614ebceddbc429f415f38da9032ea6ef2a92b"),
    ReviewedPin(path="sealed/cases/bookshop_task_completion.json", sha256="170dd925880b035c3a999512c982aaccaa2deda96e8d55950f4b7c14f0ce9a24"),
    ReviewedPin(path="fixtures/requests/bookshop_compare_pair_01.jsonl", sha256="749ea9360c55e8340ccd995234c3e333d66d0740cfb02e227223c60c9c406005"),
    ReviewedPin(path="fixtures/requests/bookshop_compare_pair_01_specs.json", sha256="c6b5b4b09f71edf6480a4b88d026115029ff81d1dbfd02a9d1d155718da56c10"),
    ReviewedPin(path="fixtures/requests/bookshop_compare_pair_02.jsonl", sha256="43b5e8275ceb4a4fb444e26232fde303c7e4feb35ae8976bb443a3c143a21de5"),
    ReviewedPin(path="fixtures/requests/bookshop_compare_pair_02_specs.json", sha256="78294186d99b589ac577a282d6930978e02c9ae137836c1f57e0871ebb061c08"),
    ReviewedPin(path="fixtures/requests/bookshop_compare_pair_03.jsonl", sha256="c0e0ed996c2cc6f05971be34ceb68daadb36aa838d6a1344d2d3e13b1000bb0f"),
    ReviewedPin(path="fixtures/requests/bookshop_compare_pair_03_specs.json", sha256="0a05eb2d8ccd74861119570c0269b20781036e62c89e2f0297039e37744005fe"),
)


# Exact Northline contents approved by the operator on 2026-10-03.
_NORTHLINE_PINS = (
    ReviewedPin(path="fixtures/catalogs/northline_v1.json", sha256="0c9376b30384fcac93a44ed858ce96b4e8eb8f46be75f67b0f3363c769bbca34"),
    ReviewedPin(path="fixtures/documents/northline/acceptance_contract.md", sha256="545e1221a46e84c9f6446db40966e9fa1e9791f18a34f9a0305ee93c31de4949"),
    ReviewedPin(path="fixtures/documents/northline/deployment_brief.md", sha256="ab3187358a0ffecdebe4d80467b802f4137054858f684495c7c3fceef79ed461"),
    ReviewedPin(path="fixtures/documents/northline/discovery_prompts.md", sha256="22d3e41c515a86c49932d440b88c6e3c75e2615f0ba33ac6ff6d01fdd0e25143"),
    ReviewedPin(path="fixtures/documents/northline/handover_prompts.md", sha256="5b6ec7abe14f6f56c705df109802129a76e5563c4de3459f384adac78ac48ab5"),
    ReviewedPin(path="fixtures/documents/northline/permissions_policy.json", sha256="7c1a220108e6ba2ae733b7319429dd88f889dfc0188e0d8282cb17a88ccb2468"),
    ReviewedPin(path="fixtures/documents/northline/rollout_checklist.md", sha256="226389080b348b0dceab81afd5e90dc6261d69f88827d2fab8c62e1940ada518"),
    ReviewedPin(path="fixtures/mission/northline_deployment_v1.json", sha256="753bc3a26ac570e0e719003d4777dcda410fa1d5d16657603f1fd8c05020fbd1"),
    ReviewedPin(path="fixtures/requests/northline_compare_manifest.json", sha256="5d61c55311f99d30463b23230cdca53fd8b21479f7a0c57f308caa78fb8b122c"),
    ReviewedPin(path="fixtures/requests/northline_compare_pair_01.jsonl", sha256="d928534c4827ba59c73afd04586311e73a062b8de3df75826ba3fa5a8a1618b9"),
    ReviewedPin(path="fixtures/requests/northline_compare_pair_01_specs.json", sha256="23554dd0b35e574caea870339bb74b68157ed8dec422d53df0961f5bdb205ae9"),
    ReviewedPin(path="fixtures/requests/northline_compare_pair_02.jsonl", sha256="72a7b405c1e83064604fb58f058757c6e00927ad19dd0d38096c108eaa015a36"),
    ReviewedPin(path="fixtures/requests/northline_compare_pair_02_specs.json", sha256="6c8968b6367e834868fe3ce7144aabfae93b0fa5b770cf9224bd78f32d988efb"),
    ReviewedPin(path="fixtures/requests/northline_compare_pair_03.jsonl", sha256="eaf45873d79f6407f4b166520fd2c80169e9e50bfa00cea126ea7f37a1241135"),
    ReviewedPin(path="fixtures/requests/northline_compare_pair_03_specs.json", sha256="2f6f92eae314e670269292f9a8c15bc6c639b403c0b1fb9ff9ee68fec6c96b2f"),
    ReviewedPin(path="fixtures/requests/northline_deployment_incident.jsonl", sha256="2569a7275a9be04d00fb00d7be99f00dd3177122cc0e20b903e5e69343324b5b"),
    ReviewedPin(path="fixtures/state/northline_compare_state_v1.json", sha256="8cbe707cb710711b1610fa89ba527cc0c463d8e939aee22b8797ad18e2f9f36d"),
    ReviewedPin(path="fixtures/state/northline_start.json", sha256="92eb6ad28a8e26abf9e3025c3af03abf11a361b9635d51c81979dccd498e3f99"),
    ReviewedPin(path="sealed/cases/northline_deployment.json", sha256="d2f67e0655267698c3ac78458502d5e7e2aa582dfcf0755fcf9f348a4f6d04d6"),
    ReviewedPin(path="sealed/cases/northline_deployment_v2.json", sha256="c1f3c8d3369b6eeca61f8fba8a4ab4829a248a9887e14c4257d5b30a6ab56798"),
    ReviewedPin(path="templates/artifact/northline/acceptance_tests.py", sha256="01beab46acbb5adfd774cda75ab424c0496eded2c754420e9d7ad3aa9b4e5e29"),
    ReviewedPin(path="templates/artifact/northline/discovery.md", sha256="7bc2075914d6e51735edf7e3beb280112f0fbd195bf48416e865ef15ed273ba3"),
    ReviewedPin(path="templates/artifact/northline/permissions.json", sha256="9f15e943e9b7bdcf8c51b6b00fdf6a4d2a218ea20352e8742186a809ee40db40"),
    ReviewedPin(path="templates/artifact/northline/runbook.md", sha256="4cd7b797d7f2cb112132c49a38820a77c8fd24045af1e79117927142b16203a6"),
    ReviewedPin(path="templates/artifact/northline_blank_service.py", sha256="d72b4f3f7068a936451f5ec5872927d8fd1260cb64fb06347deee94698349ce0"),
)

_NORTHLINE_DOCUMENTS = (
    PackDocument(doc_id="acceptance_contract", path="fixtures/documents/northline/acceptance_contract.md",
                 sha256="545e1221a46e84c9f6446db40966e9fa1e9791f18a34f9a0305ee93c31de4949", station="Acceptance tests"),
    PackDocument(doc_id="deployment_brief", path="fixtures/documents/northline/deployment_brief.md",
                 sha256="ab3187358a0ffecdebe4d80467b802f4137054858f684495c7c3fceef79ed461", station="Deployment brief"),
    PackDocument(doc_id="discovery_prompts", path="fixtures/documents/northline/discovery_prompts.md",
                 sha256="22d3e41c515a86c49932d440b88c6e3c75e2615f0ba33ac6ff6d01fdd0e25143", station="Discovery"),
    PackDocument(doc_id="handover_prompts", path="fixtures/documents/northline/handover_prompts.md",
                 sha256="5b6ec7abe14f6f56c705df109802129a76e5563c4de3459f384adac78ac48ab5", station="Handover"),
    PackDocument(doc_id="permissions_policy", path="fixtures/documents/northline/permissions_policy.json",
                 sha256="7c1a220108e6ba2ae733b7319429dd88f889dfc0188e0d8282cb17a88ccb2468", station="Permissions"),
    PackDocument(doc_id="rollout_checklist", path="fixtures/documents/northline/rollout_checklist.md",
                 sha256="226389080b348b0dceab81afd5e90dc6261d69f88827d2fab8c62e1940ada518", station="Rollout"),
)


def _family(name, filename, family_class=FamilyClass.COMPARISON):
    return FamilyDeclaration(family=name, family_class=family_class,
                             case_file=f"sealed/cases/{filename}.json", cycle=1, min_variants=6)


_PACKS = (
    EngagementPack(
        slug="bookshop", schema_version=1,
        display=BoardDisplay(role_name="Junior Applied AI Engineer", employer=None,
                             client="Bellwether Books", room_id="bookshop",
                             station_labels=("Incident board", "Workbench", "Comparison bench",
                                             "Customer queue", "Shift handover")),
        assist=AssistPolicy(level_label="scaffolded", allowed_roles=tuple(AssistRole),
                            total_calls_per_shift=3, max_patch_proposals=1),
        mission_path="fixtures/mission/bookshop_pivot_v1.json",
        public_state_path="fixtures/shop/bookshop_pivot_public_state.json",
        comparison_state_path="fixtures/shop/bookshop_compare_state_v1.json",
        incident_request_path="fixtures/requests/bookshop_pivot_incident.jsonl",
        manifest_path="fixtures/requests/bookshop_compare_manifest.json", documents=(),
        families=tuple(_family(name, f"bookshop_{name}", FamilyClass.ATTEMPT)
                       for name in ("stale_information", "policy_exception", "hostile_instruction"))
                 + (_family("task_completion", "bookshop_task_completion"),),
        consequences=ConsequenceRules(success_events=("SALE_COMPLETED sale",), rollout_event=None,
                                      handover_record_required=False),
        reviewed_pins=_BELLWETHER_PINS,
    ),
    EngagementPack(
        slug="gtm", schema_version=1,
        display=BoardDisplay(role_name="Go-To-Market Engineer", employer="Stonebridge Software",
                             client="Revenue team", room_id="gtm",
                             station_labels=("Signal inbox", "Workflow", "Comparison bench",
                                             "Pipeline wall", "Handoff queue")),
        assist=AssistPolicy(level_label="guided", allowed_roles=(AssistRole.HINT, AssistRole.DIAGNOSIS),
                            total_calls_per_shift=2, max_patch_proposals=0),
        mission_path="fixtures/mission/gtm_pipeline_v1.json",
        public_state_path="fixtures/state/gtm_pipeline_public_state.json",
        comparison_state_path="fixtures/state/gtm_compare_state_v1.json",
        incident_request_path="fixtures/requests/gtm_pipeline_incident.jsonl",
        manifest_path="fixtures/requests/gtm_compare_manifest.json", documents=(),
        families=(_family("pipeline_ownership", "gtm_pipeline_ownership"),),
        consequences=ConsequenceRules(success_events=("OWNER_ASSIGNED owner", "SLA_CLOCK_STARTED sla"),
                                      rollout_event=None, handover_record_required=False),
        reviewed_pins=(),
    ),
    EngagementPack(
        slug="northline", schema_version=1,
        display=BoardDisplay(role_name="Forward Deployed Engineer", employer=None,
                             client="Northline Bike Cooperative", room_id="northline",
                             station_labels=("Deployment brief", "Discovery", "Permissions",
                                             "Acceptance tests", "Rollout", "Handover")),
        assist=AssistPolicy(level_label="reduced", allowed_roles=(AssistRole.HINT,),
                            total_calls_per_shift=1, max_patch_proposals=0),
        mission_path="fixtures/mission/northline_deployment_v1.json",
        public_state_path="fixtures/state/northline_start.json",
        comparison_state_path="fixtures/state/northline_compare_state_v1.json",
        incident_request_path="fixtures/requests/northline_deployment_incident.jsonl",
        manifest_path="fixtures/requests/northline_compare_manifest.json", documents=_NORTHLINE_DOCUMENTS,
        families=(_family("deployment", "northline_deployment_v2"),),
        consequences=ConsequenceRules(success_events=("BOOKING_COMMITTED booking",),
                                      rollout_event="ROLLOUT_APPROVED rollout",
                                      handover_record_required=True),
        reviewed_pins=_NORTHLINE_PINS,
    ),
)


def registered_packs() -> tuple[EngagementPack, ...]:
    return _PACKS


def resolve_pack(slug: str) -> EngagementPack:
    matches = [pack for pack in _PACKS if pack.slug == slug]
    if not matches:
        raise PackNotFound("unknown engagement")
    if len(matches) != 1:
        raise PackUnavailable("duplicate engagement declaration")
    # Revalidate even operator replacements constructed with model_copy.
    try:
        return EngagementPack.model_validate(matches[0].model_dump(mode="json"))
    except ValidationError as exc:
        raise PackUnavailable("incomplete engagement declaration") from exc
