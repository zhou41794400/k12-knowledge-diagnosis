.PHONY: check report materials bundle init-repo release tag all

PYTHON := PYTHONPYCACHEPREFIX=/private/tmp/pycache python3

check:
	$(PYTHON) -m py_compile edu_tracker/__init__.py edu_tracker/__main__.py edu_tracker/cli.py edu_tracker/materials.py edu_tracker/models.py edu_tracker/knowledge_registry.py edu_tracker/pipeline.py edu_tracker/reporting.py services/__init__.py services/edu_tracker/cli.py services/edu_tracker/materials.py services/edu_tracker/models.py services/edu_tracker/knowledge_registry.py services/edu_tracker/pipeline.py services/edu_tracker/reporting.py

report:
	$(PYTHON) -m edu_tracker report

materials:
	$(PYTHON) -m edu_tracker materials

all: check report materials

bundle:
	sh scripts/build_transfer_bundle.sh

init-repo:
	@test -n "$(TARGET)" || (echo "请通过 TARGET=/path/to/repo 指定目标目录" >&2; exit 1)
	sh scripts/init_independent_repo.sh "$(TARGET)"

release:
	@test -n "$(VERSION)" || (echo "请通过 VERSION=0.1.1 指定版本号" >&2; exit 1)
	sh scripts/generate_release_note.sh "$(VERSION)"

tag:
	@test -n "$(VERSION)" || (echo "请通过 VERSION=0.1.1 指定版本号" >&2; exit 1)
	sh scripts/create_git_tag.sh "$(VERSION)"
