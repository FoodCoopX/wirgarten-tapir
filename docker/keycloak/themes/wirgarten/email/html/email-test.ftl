<#import "template.ftl" as layout>
<@layout.emailLayout realmName>
${kcSanitize(msg("emailTestBodyHtml",realmName))?no_esc}
</@layout.emailLayout>
