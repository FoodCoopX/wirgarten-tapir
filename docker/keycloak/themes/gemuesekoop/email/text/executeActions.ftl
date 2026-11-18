<#ftl output_format="plainText">
<#assign requiredActionsText><#if requiredActions??><#list requiredActions><#items as reqActionItem>${msg("requiredAction.${reqActionItem}")}<#sep>, </#sep></#items></#list><#else></#if></#assign>
<#assign activation = requiredActions?? && requiredActions?size == 1 && requiredActions?seq_contains("VERIFY_EMAIL")>

${msg(activation?then("gkActivationBody", "executeActionsBody"), link, linkExpiration, realmName, requiredActionsText, linkExpirationFormatter(linkExpiration))}
