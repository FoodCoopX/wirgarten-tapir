<#import "template.ftl" as layout>
<@layout.emailLayout realmName>
${kcSanitize(msg("eventLoginErrorBodyHtml",event.date,event.ipAddress))?no_esc}
</@layout.emailLayout>
