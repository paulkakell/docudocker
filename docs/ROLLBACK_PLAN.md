# Rollback plan

1. Retain the previous tagged image and source artifact.
2. If deployment fails, redeploy the prior image tag.
3. Restore the previous compose file or environment variable set if configuration drift caused the regression.
4. Verify `/healthz` and the Overview tab after rollback.
5. Review structured logs for the failing request path and correct the issue before retrying deployment.
