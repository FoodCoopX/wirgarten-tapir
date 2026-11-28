export const EMAIL_DISPATCH_STATUS_PROPS = {
  opened: {
    color: "success",
    text: "Geöffnet",
    extraText:
      "Es kann sicher davon ausgegangen werden, dass die Mail angekommen ist. Beachte: Wenn Mitglieder ein Mailprogramm nutzen, das Bilder blockiert (z.B. Thunderbird tut das standardmäßig oder auch Posteo im Browser), dann kann der Status nicht korrekt erfasst werden und Mails werden ggf. nicht als geöffnet angezeigt, obwohl sie gelesen wurden.",
  },
  error: {
    color: "danger",
    text: "Fehler beim Versand",
    extraText:
      "Der Versand ist fehlgeschlagen. Bitte wende dich an FoodCoopX über das Ticketportal.",
  },
  bounced: {
    color: "danger",
    text: "Bounce",
    extraText:
      "Der Mail-Server des Empfängers hat die Mail verweigert. In der Regel ist die Mailbox voll. Bitte wende dich im ersten Schritt an das betreffende Mitglied und bitte um Klärung.",
  },
  unknown: {
    color: "warning",
    text: "Nicht geöffnet",
    extraText:
      "Die Email hat unseren Mail-Server verlassen. Wir haben keine Infos, ob sie angekommen oder geöffnet worden ist. Es gab aber zumindest keinen Fehler beim Versand. Wende dich im Zweifel im ersten Schritt an das Mitglied, um herauszufinden, ob die Mail doch im Posteingang oder SPAM-Ordner gelandet ist.",
  },
  sending: {
    color: "info",
    text: "Wird versendet",
    extraText:
      "Die Mail ist vorbereitet worden aber noch nicht versendet. Der Versand müsste in den kommenden 1-2 Minuten erfolgen. Wenn die Mail länger in dem Status hängen bleibt, dann wende dich an FoodCoopX über das Ticketportal.",
  },
  delivered: {
    color: "primary",
    text: "Zugestellt",
    extraText:
      "Es kann sicher davon ausgegangen werden, dass die Mail angekommen ist. Die Mail ist vermutlich noch nicht geöffnet worden.",
  },
};
