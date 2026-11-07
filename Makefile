.PHONY: test test_core demo

space := $(subst ,, )

# Runs the tests with path_coverage measuring its own src/ and test/,
# each a group, code and test, its report in reports/paths. tids runs
# only the tests whose id contains one of its values.
#   eg make test tids='5be7c0 e2b45f01'
test:
	bash ${PWD}/bin/test.sh $(if $(tids),-k "$(subst $(space), or ,$(strip $(tids)))")

# Runs every test but the generated ones in test/property, and checks the
# result: whether the hand-written tests alone reach full coverage.
test_core:
	bash ${PWD}/bin/test.sh --suite core

# Build the demo report into site/, the same site GitHub Pages
# publishes, and open it in a browser where one can be found.
demo:
	${PWD}/bin/build_demo.sh
	@if command -v open > /dev/null; then open ${PWD}/site/index.html; \
	elif command -v xdg-open > /dev/null; then xdg-open ${PWD}/site/index.html; fi
