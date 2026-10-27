<#import "template.ftl" as layout>
<@layout.emailLayout realmName>
${kcSanitize(msg("eventUpdateTotpBodyHtml",event.date, event.ipAddress))?no_esc}
</@layout.emailLayout>
