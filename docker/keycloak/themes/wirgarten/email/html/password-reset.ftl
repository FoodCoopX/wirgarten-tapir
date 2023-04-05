<#import "template.ftl" as layout>
<@layout.layout realmName>
${kcSanitize(msg("passwordResetBodyHtml",link, linkExpiration, realmName, linkExpirationFormatter(linkExpiration)))?no_esc}
</@layout.layout>