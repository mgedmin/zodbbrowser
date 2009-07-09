from zope.interface import Interface


class IValueRenderer(Interface):
    """Renderer of attribute values."""

    def render(tid=None):
        """Render object value to HTML.

        Hyperlinks to other persistent objects will be limited to versions
        at or older than the specified transaction id (``tid``).
        """


class IStateInterpreter(Interface):
    """Interprets persistent object state.

    Usually you adapt a tuple (object, state, tid) to IStateInterpreter to
    figure out how a certain object type represents its state for pickling.
    The tid may be None or may be a transaction id, and is supplied in case
    you need to look at states of other objects to make a full sense of this
    one.
    """

    def listAttributes():
        """Return the attributes of this object as tuples (name, value).

        The order of the attributes returned is irrelevant.

        May return None to indicate that this kind of object cannot
        store attributes.
        """

    def listItems():
        """Return the items of this object as tuples (name, value).

        The order of the attributes returned matters.

        Often these are not stored directly, but extracted from an attribute
        and presented as items for convenience.

        May return None to indicate that this kind of object is not a
        container and cannot store items.
        """

    def getParent():
        """Return the parent of this object."""

    def getName():
        """Return the name of this object."""

    def asDict():
        """Return the state expressed as an attribute dictionary.

        The state should combine the attributes and items somehow, to present
        a complete picture for the purpose of comparing these dictionaries
        while looking for changes.
        """

