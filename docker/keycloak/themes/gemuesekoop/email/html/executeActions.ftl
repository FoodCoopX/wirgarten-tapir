<#outputformat "plainText">
<#assign requiredActionsText><#if requiredActions??><#list requiredActions><#items as reqActionItem>${msg("requiredAction.${reqActionItem}")}<#sep>, </#sep></#items></#list></#if></#assign>
</#outputformat>
<#assign activation = requiredActions?? && requiredActions?size == 1 && requiredActions?seq_contains("VERIFY_EMAIL")>

<#import "template.ftl" as layout>
<@layout.emailLayout>
${kcSanitize(msg(activation?then("gkActivationBodyHtml", "executeActionsBodyHtml"), link, linkExpiration, realmName, requiredActionsText, linkExpirationFormatter(linkExpiration)))?no_esc}
</@layout.emailLayout>
