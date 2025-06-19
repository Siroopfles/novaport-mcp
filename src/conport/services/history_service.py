from sqlalchemy import event, select
from sqlalchemy.orm import Session, attributes

from ..db import models


def _add_history(target, history_model, change_source):
    attributes.instance_state(target)
    content_history = attributes.get_history(target, "content")
    if not content_history.deleted:
        return
    old_content = content_history.deleted[0]
    session = Session.object_session(target)
    if not session:
        return
    latest_version_stmt = (
        select(history_model.version).order_by(history_model.version.desc()).limit(1)
    )
    latest_version = session.execute(latest_version_stmt).scalar_one_or_none() or 0
    new_history_record = history_model(
        version=latest_version + 1, content=old_content, change_source=change_source
    )
    session.add(new_history_record)


def setup_history_listeners():
    @event.listens_for(models.ProductContext, "after_update")
    def receive_after_product_update(mapper, connection, target: models.ProductContext):
        _add_history(target, models.ProductContextHistory, "ProductContext Update")

    @event.listens_for(models.ActiveContext, "after_update")
    def receive_after_active_update(mapper, connection, target: models.ActiveContext):
        _add_history(target, models.ActiveContextHistory, "ActiveContext Update")


setup_history_listeners()
