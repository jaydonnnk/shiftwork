"""Render composition of the existing single-process controller and live guards."""

from contextlib import asynccontextmanager
from decimal import Decimal
import os
import platform
import uuid

from contree_client.httpx import ContreeAsyncClient

from shiftwork import config
from shiftwork.app import create_app
from shiftwork.assist.gateway import LiveAssistGateway
from shiftwork.live_budget import LiveComparisonBudget, LiveOperationBudget

PERMISSIONS = ('cancel', 'import', 'list', 'set_image_tag', 'spawn', 'spawn_disposable')
# Existing conservative projection rates, not a claim of a current vendor quote.
INPUT_RATE = Decimal('0.06')
OUTPUT_RATE = Decimal('0.24')


def operation_budget() -> LiveOperationBudget:
    return LiveOperationBudget(config.SERVICE_MODEL, INPUT_RATE, OUTPUT_RATE)


def comparison_budget() -> LiveComparisonBudget:
    return LiveComparisonBudget(config.SERVICE_MODEL, INPUT_RATE, OUTPUT_RATE)


def create_hosted_app(db_path: str | None = None):
    token = os.environ.get('NEBIUS_API_KEY', '')
    project = os.environ.get('NEBIUS_PROJECT_ID', '')
    live = bool(token and project)
    if live and (token != token.strip() or project != project.strip()
                 or not project.startswith('aiproject-')):
        raise RuntimeError('Invalid hosted credential configuration')
    app = create_app(
        db_path, executor='tokenfactory' if live else 'recorded',
        assist_gateway=LiveAssistGateway(token) if live else None,
        live_operation_budget=operation_budget if live else None,
        live_comparison_budget=comparison_budget if live else None,
    )
    app.state.hosted_runtime = {
        'hosted': True, 'configured_executor': app.state.executor,
        'python_version': platform.python_version(), 'boot_id': str(uuid.uuid4()),
        'preflight_permissions': None,
        'notice': (
            f'Hosted {app.state.executor} executor: shared practice demo. '
            + ('Token Factory diagnostics, eligible selected operations and help are enabled. '
               'The first Bellwether baseline remains a labelled saved inspection. ' if live else
               'Recorded fallback: saved inspections are replayed; comparisons and selected '
               'operations can run pinned fixtures as TRUSTED_LOCAL. No live inference. ')
            + 'Free hosting sleeps after 15 idle minutes; waking may take about a minute. '
              'Sleep, restart or redeploy begins a fresh practice database. '
              'Download the build to keep your own history.'
        ),
    }
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def hosted_lifespan(app):
        if live:
            client = ContreeAsyncClient(token, project=project, timeout=20)
            try:
                response = await client.whoami()
                permissions = {name: response.permissions.get(name) is True for name in PERMISSIONS}
                if not all(permissions.values()):
                    raise RuntimeError('missing Sandbox permission')
                app.state.hosted_runtime['preflight_permissions'] = permissions
            except Exception:
                raise RuntimeError('Hosted Sandbox preflight failed') from None
            finally:
                await client.close()
        async with original_lifespan(app):
            yield

    app.router.lifespan_context = hosted_lifespan
    return app
