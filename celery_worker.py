from celery import Celery

def make_celery(app=None):
    """
    Khởi tạo Celery với Flask app context.
    Redis làm Message Broker (mặc định: redis://localhost:6379/0)
    """
    celery_app = Celery(
        'ads_manager',
        broker='redis://localhost:6379/0',
        backend='redis://localhost:6379/0',
        include=['app.tasks']
    )

    if app:
        celery_app.conf.update(
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='Asia/Ho_Chi_Minh',
            enable_utc=True,
        )

        class ContextTask(celery_app.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery_app.Task = ContextTask

    return celery_app


# Instance toàn cục - dùng khi worker khởi động độc lập
celery = make_celery()
