# Theo's wishes for Tapir

This document doesn't really belong in the repo, but I had done a similar list and lost it once, so I'm committing it
here so that it doesn't happen again.

It's a list of all the things I would like to improve, if I had infinite time and energy. It's more of a mind dump than
a constructed list, meaning it's neither sorted nor fully thought through.
That said, if you feel like tackling some of its point, do feel free to do so. Don't hesitate to ask me questions
through the matrix channel or by tagging me in issues or PRs.

- Make the payments more robust:
    - Currently, the Payment model saves the type as a string, which is very brittle: things will break if the name of a
      product type changes. We should use foreign keys to the corresponding product type (ideally even to the contract),
      same for coop shares, solicontribution...
    - It should be easier to trace how a Payment got created, both from the data and when displayed in a member's
      payment list: the whole formula should be displayed. For example when trial period payments for single deliveries
      are calculated it gets complicated.
    - Same for MemberCredits.
    - Payments are quite complex, meaning the payment builder services are complex too, but maybe they can be improved
      on
- We can probably squash many migrations, hoping to make setting up a new local instance from a blank state faster
- The mail module is currently a separate private repo, but it's only used by Tapir. It should be integrated directly
  into Tapir instead
    - Hopefully the build if the frontend part of the mail module can use the same process as Tapir
    - The code quality of the mail module may not be up to par with the newest Tapir code
- The import of member data currently goes through the import-data command, which is inconvenient and untested.
    - Solawis should be able to import data themselves, ideally from they choice of excel, csv, libreoffice files
    - They should be able to download a template file in their chosen format with the appropriate column names
    - They should get detailed feedback on errors if any
- I don't like the UI structure of the page Vertragsperiode & Produkte, for example I think it makes sense to always
  show products and product types.
    - Also, it's not clear which of the product fields are time-dependent, like the product type capacity or the product
      price. It's also not clear that the price will be set later
    - The current frontend is a messy django template
    - The code for saving products and product types is a mess
- The current config page is messy and inconvenient
    - UX can be improved (though I'm not sure how)
    - Some fields rely on an exact format (like a list separated with ;), we should have frontend helpers for that
- There should be an "superadmin" role, separate from the solawi admin role, that is allowed to change all config
  parameters
    - Some parameters can only be changed in DEBUG mode, because changing them on a live instance could produce invalid
      data. This is annoying when setting up a new instance because it means Marcus can't do the config himself.
- The navbar at the top should have a search field that searches members, and goes straight to a member's page if an
  exact member number is given
- The per-request cache can be improved on
    - We should type the cache parameters in most functions as a name type to distinguish it from just a dict. Maybe it
      could be a dataclass to ensure the type of the data
    - It should be enforced that each key belongs to a category (categories are used for clearing the cache)
    - We only have a per-request cache for now because it reduces the cases where we need to invalidate it a lot, but
      maybe some of the things have an easy path and should be in redis?
        - Not sure it's worth the added complexity
- The code for the frontend bestell wizard can probably be improved on a lot. Also, it would need tests
- In some complex views I pass the serializer's data as dict to the service. That should never be the case, we should
  pass deserialized parameters instead, in a data class if it's too many parameters
- There are a few places where we let admins configure strings with tokens, typically in the bestell wizard, but some
  use {} and some use {{}}, we should be consistent.