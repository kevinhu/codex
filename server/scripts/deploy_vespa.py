# %%
from vespa.package import ApplicationPackage, Field, FieldSet
from vespa.deployment import VespaDocker

# %%
app_package = ApplicationPackage(name="codex")
app_package.schema.add_fields(
    Field(
        name="id",
        type="string",
        indexing=["attribute", "summary"],
        attribute=["fast-search"],
    ),
    Field(
        name="name",
        type="string",
        indexing=["index", "summary"],
        index="enable-bm25",
    ),
    Field(
        name="type",
        type="string",
        indexing=["attribute", "summary"],
        attribute=["fast-search"],
    ),
    Field(
        name="slug",
        type="string",
        indexing=["index", "summary"],
        index="enable-bm25",
    ),
    Field(
        name="description",
        type="string",
        indexing=["index", "summary"],
        index="enable-bm25",
    ),
)

# %%
app_package.schema.add_field_set(
    FieldSet(name="default", fields=["name", "slug", "description"])
)

# %%
vespa_docker = VespaDocker()
vespa_app = vespa_docker.deploy(application_package=app_package)

# %%
