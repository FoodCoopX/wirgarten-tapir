<#import "template.ftl" as layout>
<@layout.emailLayout realmName>
${kcSanitize(msg("emailUpdateConfirmationBodyHtml",link, newEmail, realmName, linkExpirationFormatter(linkExpiration)))?no_esc}
</@layout.emailLayout>
