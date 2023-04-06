<#outputformat "plainText">
<#assign requiredActionsText><#if requiredActions??><#list requiredActions><#items as reqActionItem>${msg("requiredAction.${reqActionItem}")}<#sep>, </#sep></#items></#list></#if></#assign>
</#outputformat>

<#import "template.ftl" as layout>
<#assign linkExpirationInHours = (linkExpiration / 60)?round>
<@layout.emailLayout realmName>
${kcSanitize(msg("executeActionsBodyHtml",link, linkExpirationInHours, realmName, requiredActionsText, linkExpirationFormatter(linkExpiration)))?no_esc}
</@layout.emailLayout>