SRC_DIR=./minikv

lint:
	pylint ${SRC_DIR}
	mypy ${SRC_DIR} 

install:
	pip install -e .

test-no-replication:
	python ./test_runner.py none

quick-test-chain-replication:
	python ./test_runner.py chain --scale-factor=1

test-chain-replication:
	python ./test_runner.py chain --scale-factor=10

serve-no-replication: 
	python -c "from minikv import run; run();" none

submit-check:
	@if ! test -d .git; then \
		echo No .git directory, is this a git repository?; \
		false; \
	fi
	@if ! git diff-files --quiet || ! git diff-index --quiet --cached HEAD; then \
		git status -s; \
		echo; \
		echo "You have uncomitted changes.  Please commit or stash them."; \
		false; \
	fi
	@if test -n "`git status -s`"; then \
		git status -s; \
		read -p "Untracked files will not be handed in.  Continue? [y/N] " r; \
		test "$$r" = y; \
	fi

zipball: submit-check
	git archive --verbose --format zip --output submission.zip HEAD


