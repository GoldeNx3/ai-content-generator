from app.models import ArticleFixIssue

def update_failure(report,status,reason):
    report.status=status
    if status=='failed' and not report.issues:
        report.issues=[ArticleFixIssue(qa_issue_id=issue['id'],status='failed',reason=reason)
            for issue in report.input_snapshot.get('issues',[])]
