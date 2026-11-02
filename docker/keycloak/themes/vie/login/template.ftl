<#macro registrationLayout bodyClass="" displayInfo=false displayMessage=true displayRequiredFields=false>
<!DOCTYPE html>
<html <#if realm.internationalizationEnabled> lang="${locale.currentLanguageTag}"</#if>>

<head>
  <link href="https://fonts.googleapis.com/css?family=Roboto:100,300,400,500,700,900|Material+Icons" rel="stylesheet" type="text/css">
  <link href="https://cdn.jsdelivr.net/npm/quasar@2.14.1/dist/quasar.prod.css" rel="stylesheet" type="text/css">
  <meta charset="utf-8">
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta name="robots" content="noindex, nofollow">

  <#if properties.meta?has_content>
    <#list properties.meta?split(' ') as meta>
      <meta name="${meta?split('==')[0]}" content="${meta?split('==')[1]}"/>
    </#list>
  </#if>
  <title>${msg("loginTitle",(realm.displayName!''))}</title>
  <link rel="icon" href="${url.resourcesPath}/img/favicon.ico" />
</head>

<body>
  <div id="q-app">
    <div class="window-height window-width row justify-center bg-grey-4">
      <!-- 
        Header 
      -->
      <div class="full-width row justify-center">
        <#include "fragments/header.ftl">
      </div>
      <!-- 
        Content 
      -->
      <div class="row justify-center" style="max-width: 500px;"> 
        <q-card class="full-width bg-white column justify-center">
          <!-- banner -->
          <div>
            <#include "fragments/banner.ftl">
          </div>
          <!-- form -->
          <div :class="{ 'q-pt-md q-pr-md q-pl-md': $q.screen.xs, 'q-pt-lg q-pr-lg q-pl-lg': $q.screen.gt.xs }"> 
            <#nested "form">
          </div>
        </q-card>
        <!-- global options -->
        <div :class="{ 'q-pt-xs': $q.screen.xs, 'q-pt-sm': $q.screen.gt.xs }">
          <#include "fragments/options.ftl">
        </div>
      </div>
      <!-- 
        Footer 
      -->
      <div class="full-width row justify-center">
        <#include "fragments/footer.ftl">
      </div>
  </div>
  <!-- 
    Use Vue and Quasar with UMD version
    For more information, refer to https://quasar.dev/start/umd#installation
  -->
  <script src="https://cdn.jsdelivr.net/npm/vue@3/dist/vue.global.prod.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/quasar@2.14.1/dist/quasar.umd.prod.js"></script>
  <script src="${url.resourcesPath}/js/config.js"></script>  
  <script src="${url.resourcesPath}/js/quasar.js"></script>
  <!-- Install Quasar language pack -->
  <#if properties.locales?has_content>
    <#list properties.locales?split(',') as locale>
      <script>Quasar.lang.set(Quasar.lang.${locale})</script>
    </#list>      
  </#if> 
</body>
</html>
</#macro>
