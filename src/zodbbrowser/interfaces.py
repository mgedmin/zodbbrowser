from zope.interface import Interface


class IObjectHistory(Interface):
    """History of persistent object state.

    Adapt a persistent object to IObjectHistory.
    """

    def __len__():
        """Return the number of history records."""

    def __getitem__(n):
        """Return n-th history record.

        Records are ordered by age, from latest (index 0) to oldest.

        Each record is a dictonary with at least the following items:

            tid -- transaction ID (a byte string, usually 8 bytes)
            time -- transaction timestamp (Unix time_t value)
            user_name -- name of the user responsible for the change
            description -- short description (often a URL)

        """

    def lastChange(tid=None):
        """Return the last transaction at or before tid.

        If tid is not specified, returns the very last transaction that
        modified this object.

        Will raise KeyError if object did not exist before the given
        transaction.
        """

    def loadState(tid=None):
        """Load and return the object's historical state at or before tid.

        Returns the unpicked state, not an actual persistent object.
        """

    def loadStatePickle(tid=None):
        """Load and return the object's historical state at or before tid.

        Returns the picked state as a string.
        """

    def rollback(tid):
        """Roll back object state to what it was at or before tid."""


class IDatabaseHistory(Interface):
    """History of the entire database.

    Adapt a connection object to IObjectHistory.
    """

    def __iter__(n):
        """Return an iterator over the history record.

        Records are ordered by age, from oldest (index 0) to newest.

        Each record provides ZODB.interfaces.an IStorageTransactionInformation.
        """


class IValueRenderer(Interface):
    """Renderer of attribute values."""

    def render(tid=None, can_link=True):
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

    def getError():
        """Return an error message, if there was an error loading this state."""

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

