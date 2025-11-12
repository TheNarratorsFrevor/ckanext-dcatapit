# this is a namespace package
import logging

from ckanext.dcatapit.model.license import License, LocalizedLicenseName

from ckanext.dcatapit.model.subtheme import ThemeToSubtheme, Subtheme, SubthemeLabel

from ckanext.dcatapit.model.vocabulary import *
from ckanext.dcatapit.model.license import *
from ckan.model import meta
log = logging.getLogger(__name__)
import sqlalchemy as sa
__all__ = ['setup']


# Defensive binding: if meta provides an engine or the Session has a bind,
# ensure meta.metadata is bound so older Table APIs that rely on metadata.bind
# continue to work in environments where metadata wasn't previously bound.
try:
    _engine = getattr(meta, 'engine', None) or (hasattr(meta, 'Session') and meta.Session.get_bind())
    if _engine is not None and getattr(meta, 'metadata', None) is not None:
        try:
            # Only set if not already bound
            if getattr(meta.metadata, 'bind', None) is None:
                meta.metadata.bind = _engine
        except Exception:
            # non-fatal; fallback code paths will use explicit binds
            pass
except Exception:
    pass


def _get_bind():
    """Return a SQLAlchemy Engine/Connection to bind table operations to.

    Tries common locations on CKAN's `meta`: `meta.engine`, `meta.metadata.bind`,
    or the session bind via `meta.Session.get_bind()`.
    """
    # Try meta.engine
    try:
        engine = getattr(meta, 'engine', None)
        if engine is not None:
            return engine
    except Exception:
        pass

    # Try metadata.bind
    try:
        engine = getattr(meta, 'metadata', None)
        if engine is not None and getattr(engine, 'bind', None) is not None:
            return engine.bind
    except Exception:
        pass

    # Finally, try the session bind
    try:
        # meta.Session is typically a scoped_session or SessionProxy
        return meta.Session.get_bind()
    except Exception:
        try:
            return getattr(meta.Session, 'bind', None)
        except Exception:
            return None


def setup_db():
    log.debug('Setting up DCATAPIT tables...')
    created = setup_vocabulary_models()
    created = setup_subtheme_models() or created
    created = setup_license_models() or created

    return created


def setup():
    """Compatibility wrapper used elsewhere: call setup_db()."""
    return setup_db()


def setup_vocabulary_models():
    created = False

    # Setting up tag multilang table
    # Prefer explicit engine binding for SQLAlchemy 1.4+
    engine = getattr(meta, 'engine', None) or meta.Session.get_bind()
    if engine is None:
        # fallback to the previous helper; will still raise later when using Table APIs
        engine = _get_bind()

    inspector = sa.inspect(engine)
    if inspector.has_table(dcatapit_vocabulary_table.name):
        log.debug(f'DCATAPIT: table {dcatapit_vocabulary_table.name} already exists')
    else:
        try:
            log.info(f'DCATAPIT: creating table {dcatapit_vocabulary_table.name}')
            # Use checkfirst to be safe on newer SQLAlchemy versions
            dcatapit_vocabulary_table.create(engine, checkfirst=True)
            created = True
        except Exception as err:
            # Make sure the table does not remain incorrectly created
            try:
                if inspector.has_table(dcatapit_vocabulary_table.name):
                    dcatapit_vocabulary_table.drop(engine, checkfirst=True)
                    try:
                        meta.Session.rollback()
                    except Exception:
                        pass
            finally:
                raise err

        log.debug('DCATAPIT Tag Vocabulary table created')

    return created


def setup_subtheme_models():
    created = False
    engine = getattr(meta, 'engine', None) or meta.Session.get_bind()
    if engine is None:
        engine = _get_bind()

    inspector = sa.inspect(engine)
    for t in (Subtheme.__table__,
              SubthemeLabel.__table__,
              ThemeToSubtheme.__table__,
              ):
        if not inspector.has_table(t.name):
            log.info(f'DCATAPIT: creating table {t.name}')
            t.create(engine, checkfirst=True)
            created = True
        else:
            log.debug(f'DCATAPIT: table {t.name} already exists')

    return created


def setup_license_models():
    created = False
    engine = getattr(meta, 'engine', None) or meta.Session.get_bind()
    if engine is None:
        engine = _get_bind()

    inspector = sa.inspect(engine)
    for t in (License.__table__,
              LocalizedLicenseName.__table__,
              ):
        if not inspector.has_table(t.name):
            log.info(f'DCATAPIT: creating table {t.name}')
            t.create(engine, checkfirst=True)
            created = True
        else:
            log.debug(f'DCATAPIT: table {t.name} already exists')

    return created
