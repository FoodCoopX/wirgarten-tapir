<div :class="{ 'q-pt-xs': $q.screen.xs, 'q-pt-sm text-subtitle1':  $q.screen.gt.xs }">
  ${kcSanitize(msg("loginTitleHtml",(realm.displayNameHtml!'')))?no_esc}
</div>