Version 0.3.1
-------------
* Fixed issue with CssClass.templates field which could become corrupt via a
  roundtrip through JSON. (It ended up with things like "u['']" etc.)  If this
  affects you, you will need to manual check this field and correct it.

Version 0.3
-----------
* Compatibility with django-cms 2.3 and 2.4
* Grouping of CSS classes by category
* Button to open editor in new tab
* UI improvements
* Fixed typo that caused complete failure of semantic plugin under jQuery 1.4.2
* Other bug fixes

Version 0.2.1
-------------

* Fixed packaging bug (no templates or static media)

Version 0.2
-----------

* 'inner row' and 'inner column' commands
* Added ability to group CSS classes by category
* Compatibility with Django 1.3 and django-cms 2.1.3
* Lots of bug fixes and refinements


Version 0.1
-----------

Initial release


