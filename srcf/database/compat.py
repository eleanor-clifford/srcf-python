from __future__ import unicode_literals

import warnings

__all__ = ["MemberCompat", "SocietyCompat", "AdminsSetCompat"]


class MemberCompat(object):
    @property
    def firstname(self):
        """
        Deprecated

        .. seealso:: :attr:`preferred_name`
        """
        warnings.warn("firstname is deprecated (use preferred_name)",
                      DeprecationWarning)
        return self.preferred_name

    @property
    def initials(self):
        """Deprecated: guesses the member's initials"""
        warnings.warn("initials is deprecated (no longer stored)",
                      DeprecationWarning)
        return self.preferred_name[0].upper() + "."

    @property
    def status(self):
        """
        Deprecated: old memberlist's "status" column

        * "member" if this Member is a member, but not a user
        * "user" if this Member is a member and a user
        * "terminated" if this Member is not a member
          (and therefore cannot be a user)

        .. seealso:: :attr:`member`, :attr:`user`
        """
        warnings.warn("status is deprecated (use member and user attributes)",
                      DeprecationWarning)
        if self.member:
            if self.user:
                return "user"
            else:
                return "member"
        else:
            return "terminated"

    @property
    def joindate(self):
        """
        Deprecated: `joined` as a YYYY/MM string

        .. seealso:: :attr:`joined`
        """
        warnings.warn("joindate is deprecated (use joined)",
                      DeprecationWarning)
        return self.joined.strftime("%Y/%m")

    def socs(self, socs=None):
        warnings.warn("socs is deprecated (use societies)",
                      DeprecationWarning)
        if socs is not None:
            warnings.warn("the socs argument is ignored")
        return self.societies


class SocietyCompat(object):
    @property
    def name(self):
        warnings.warn("name is deprecated (use society)",
                      DeprecationWarning)
        return self.society

    @property
    def joindate(self):
        """
        Deprecated: `joined` as a YYYY/MM string

        .. seealso:: :attr:`joined`
        """
        warnings.warn("joindate is deprecated (use joined)",
                      DeprecationWarning)
        return self.joined.strftime("%Y/%m")

# in the old API, admins was a method


class AdminsSetCompat(set):
    def __call__(self, memberdict=None):
        if memberdict is not None:
            warnings.warn("the memberdict argument is ignored")
        warnings.warn("admins is now an attribute", DeprecationWarning)
        return self
