---
name: create-oci-module
description: Plan and create ansible.oci modules when explicitly invoked by the user.
---

# Create OCI modules

Use this skill only when the user invokes `$create-oci-module`. Confirm the working collection is `ansible.oci` before planning changes.

## Plan the module

- Accept the requested module or OCI resource and an optional Jira ticket key or number. Resolve a bare number only when the Jira project is known; otherwise ask for the full key. Read the issue and relevant comments with available Jira access, and carry its requirements and acceptance criteria into the plan. If Jira is unavailable, ask the user for the ticket content; do not invent it. Do not require a ticket when none was supplied.
- Inspect `plugins/module_utils/oci_resource.py`, `plugins/module_utils/oci_base.py`, and `plugins/module_utils/oci_info.py`, along with the closest resource and info modules, their tests, and documentation fragments. Understand the available base methods before designing module behavior. Follow collection conventions and use the inherited base methods wherever they support the required behavior. Override a base method only when a verified module requirement cannot be met through the existing methods and extension points; explain the reason and keep the override minimal. Avoid duplicating behavior already provided by the base classes.
- Prioritize the OCI SDK's documented functionality. Before adding custom logic, check whether the SDK already provides the needed operation or helper, including pagination, retries, waiting, and composite operations. Use that functionality through the collection's existing wrappers where appropriate. Add custom code only for a verified SDK gap or required Ansible behavior, such as check mode and idempotency, and explain why the SDK alone is insufficient.
- Decide whether a paired `*_info` module is useful: include one when the resource has meaningful independent get or list operations and no existing module covers them. Record the decision in the plan.
- Verify uncertain OCI SDK/API method names, arguments, model fields, and response shapes against authoritative documentation or installed SDK source. If the API structure differs from the collection's regular pattern, report the verified difference and proposed handling to the developer, then wait for a decision before implementing that exception.
- Make a concise plan for the module interfaces, SDK functionality, shared helper use, documentation, and focused tests. In execution mode, proceed with the plan unless the user requested planning only or a decision is pending.

## Inspect the installed SDK with Python

- Run Python inspection in the collection's development or test environment before finalizing module options and SDK calls. Record `sys.executable`, `oci.__version__`, and `oci.__file__` so the evidence identifies the actual SDK inspected. If `import oci` fails, locate the existing SDK environment or install the collection's declared dependencies in an isolated environment.
- Inspect the relevant client class, operation, request and response models, and composite helpers. Use `dir()` to discover available methods, `inspect.signature()` for explicit arguments, and `inspect.getdoc()` or `help()` for supported keyword options and return types. A signature containing `**kwargs` is not the full list of supported options; read its documentation and implementation.
- Instantiate the relevant model locally and inspect `swagger_types` and `attribute_map` for Python field names, types, and API names. Inspect nested models and property documentation or setter source for allowed values. These mappings alone do not establish required fields, defaults, or API constraints; verify those in the SDK source and authoritative API documentation.

For example, run this with the environment's Python interpreter and replace the compute client, operation, and model with those relevant to the requested module:

```bash
python3 - <<'PY'
import inspect
import sys

import oci

print("Python:", sys.executable)
print("SDK:", oci.__version__, oci.__file__)
client_type = oci.core.ComputeClient
print("Operations:", [name for name in dir(client_type)
                      if not name.startswith("_") and callable(getattr(client_type, name))])
operation = client_type.launch_instance
print("Signature:", inspect.signature(operation))
print("Operation documentation:", inspect.getdoc(operation))
model = oci.core.models.LaunchInstanceDetails()
print("Model fields:", model.swagger_types)
print("API field names:", model.attribute_map)
print("Model constructor documentation:", inspect.getdoc(type(model).__init__))
print("Operation source file:", inspect.getfile(operation))
PY
```

- Use the observed output to confirm the module's options, SDK arguments, and expected response model. Inspect the relevant implementation with `inspect.getsource()` when the documentation leaves behavior unclear. Report SDK version differences or unresolved gaps instead of guessing.
- This inspection imports classes and constructs local models without making OCI API calls. When actual response data is needed and OCI test access is available, use the relevant get or list operation against a known test resource and inspect only the required fields. Distinguish local SDK inspection from a live API check in the verification report; neither replaces the other.

## Worktree

- Before implementing a module, create a dedicated Git worktree under `/home/rgershbu/Ansible-Content-Repos/worktrees/`. Base the worktree directory name on the module name, for example `worktrees/oci_bastion` for `oci_bastion` and its paired info module. Never put the Jira ticket key or number in that directory name. If the name is taken, choose a unique suffix while keeping the module name.
- If already working in a linked worktree at that location for the requested module, use it. Otherwise use a worktree tool that honors the required path, or `git worktree add`. Use the chosen worktree for module edits and verification. If permissions block creation, request available filesystem escalation; if it remains blocked, tell the developer and wait instead of implementing in the original checkout.

## Implement and verify

- Keep planning, design decisions, integration, review, and final verification with the primary agent on its default model. When multi-agent tools and a Sonnet model are available, assign implementation in the chosen worktree to Sonnet agents with the plan, relevant skill requirements, and explicit file ownership. Tell each agent that others may edit the repository and it must not revert their work. If delegation is unavailable, implement with the primary agent and report that fallback.
- Keep every import, parameter, helper, branch, and line purposeful. Remove unused or obsolete code. Add behavior at the narrowest appropriate layer and reuse existing abstractions without unnecessary duplication.
- Give every function and method added or modified for the module a concise Google-style docstring. Briefly describe its purpose and include `Args`, `Returns`, and `Raises` sections where applicable. For an overridden method, briefly explain in its docstring why the inherited behavior must be overridden.
- Keep the module documentation `description` concise and limited to what the module does. Put option-specific behavior, requirements, and caveats in the relevant `options` descriptions. Use top-level `notes` only for genuinely module-wide caveats. Keep examples and return documentation accurate.
- Do not add a changelog fragment solely for a new module or its paired info module. If the work also changes existing user-facing behavior, follow `CONTRIBUTING.md` for that change.
- Add focused unit tests for the behavior implemented, including resource check mode and idempotency or info get/list behavior where applicable.
- Add integration coverage for every supported create, update, and delete operation. For each operation, run check mode before the real change and assert it predicts `changed=True` without changing the OCI resource. Apply the change, then rerun the same desired state in normal and check mode and assert `changed=False` and the expected resource state. For delete, verify the resource still exists after the check-mode run and that repeating `state=absent` is unchanged. Run the relevant integration target when OCI test access is available; otherwise report that it was not run.
- Run the relevant unit and documentation or sanity checks, then review the final diff.
