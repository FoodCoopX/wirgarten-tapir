<#import "template.ftl" as layout>
<@layout.emailLayout realmName>
${kcSanitize(msg("emailVerificationBodyCodeHtml",code))?no_esc}
</@layout.emailLayout>
