lint:
	poetry run black .

test-lint:
	poetry run black --check .

test: test-lint
	find tapir -path "*/tests/*.py" | grep -q . || exit 0; \
	poetry run pytest --cov-report xml:coverage.xml

publish-docker-image:
	gh workflow -R foodcoopx/wirgarten-tapir run "Create and publish Docker image"
