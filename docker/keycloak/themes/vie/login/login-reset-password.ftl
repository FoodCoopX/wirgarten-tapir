<#import "template.ftl" as layout>
<@layout.registrationLayout displayInfo=true displayMessage=!messagesPerField.existsError('username'); section>
  <!--
      Form section
  -->
  <#if section = "form">
    <!-- Title -->
    <div 
      class="text-center column items-center"
      :class="{ 'q-pa-xs q-gutter-sm': $q.screen.xs, 'q-pa-sm q-gutter-md': $q.screen.gt.xs }"
    >
      <div class="text-subtitle1">${msg("emailForgotTitle")}</div>
      <div>${msg("emailInstruction")}</div>
    </div>
    <!-- Content  -->
    <q-form action="${url.loginAction}" method="post" class="full-width">
      <div class="q-py-xs column">
        <q-input id="username" name="username" v-model="email" filled type="text" 
          label="${msg('usernameOrEmail')}"
          :error="<#if messagesPerField.existsError('username')>true<#else>false</#if>"
          error-message="${kcSanitize(messagesPerField.getFirstError('username'))?no_esc}" 
          :hide-bottom-space="true"
        />
      </div>
      <!-- Actions -->
      <div class="q-py-xs column items-center">
        <!-- Submit actions -->
        <div :class="{ 'q-pa-sm': $q.screen.xs, 'q-pa-md': $q.screen.gt.xs }">
          <q-btn label="${msg('doSubmit')}" color="primary" :loading="resetPasswordLoading" type="submit" @click="resetPasswordLoading = true" />
        </div>
        <!-- back to login actions -->
        <div>
          <q-btn label="${kcSanitize(msg('backToLogin'))?no_esc}" color="accent" flat rounded no-caps href="${url.loginUrl}" />
        </div>
      </div>
    </q-form>
  </#if>
</@layout.registrationLayout>
