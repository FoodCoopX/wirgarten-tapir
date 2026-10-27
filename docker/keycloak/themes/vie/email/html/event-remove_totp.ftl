<#import "template.ftl" as layout>
<@layout.emailLayout realmName>
${kcSanitize(msg("eventRemoveTotpBodyHtml",event.date, event.ipAddress))?no_esc}
</@layout.emailLayout>
