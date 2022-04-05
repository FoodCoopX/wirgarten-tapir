lint:
	poetry run black .

test-lint:
	poetry run black --check .

test: test-lint
	poetry run pytest --cov-report xml:coverage.xml

publish-docker-image:
	gh workflow -R foodcoopx/wirgarten-tapir run "Create and publish Docker image"
