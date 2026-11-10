<#ftl output_format="HTML">
<#macro emailLayout>
<!DOCTYPE html>
<html lang="${locale.language}" dir="${(ltr)?then('ltr','rtl')}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Gemüsekoop Köln e.V.</title>
</head>
<body style="margin:0; padding:0; background-color:#f7f6f2; color:#1d231c;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f7f6f2;">
    <tr>
        <td align="center" style="padding:24px 12px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                   style="max-width:600px; background-color:#ffffff; border:1px solid #e1dfd9; border-radius:12px;">
                <tr>
                    <td align="center" style="padding:24px; border-bottom:4px solid #209d50;">
                        <a href="https://www.gemuesekoop.de/">
                            <img src="https://images.squarespace-cdn.com/content/v1/67df0fa9c6a85e2640bf6ec0/f4be02f3-6fc9-4b05-bedd-9603ea9a5004/Insta+Logo+2024.jpg?format=300w"
                                 width="120" height="120" alt="Gemüsekoop Köln e.V."
                                 style="display:block; width:120px; height:120px; border:0;">
                        </a>
                        <p style="margin:16px 0 0; font-family:'Nunito Sans',Arial,sans-serif; font-size:22px; font-weight:bold; color:#1d231c;">Gemüsekoop Köln e.V.</p>
                    </td>
                </tr>
                <tr>
                    <td style="padding:28px 24px; font-family:'Nunito Sans',Arial,sans-serif; font-size:16px; line-height:26px; color:#1d231c;">
                        <#nested>
                    </td>
                </tr>
                <tr>
                    <td style="padding:20px 24px; background-color:#eeede7; font-family:Arial,sans-serif; font-size:14px; line-height:22px; color:#1d231c;">
                        <strong>Gemüsekoop Köln e.V.</strong><br>
                        Widdersdorfer Landstraße 103 · 50859 Köln<br>
                        <a href="mailto:support@gemuesekoop.de" style="color:#176e38;">support@gemuesekoop.de</a><br><br>
                        <a href="https://www.gemuesekoop.de/" style="color:#176e38;">${msg("gkWebsite")}</a> ·
                        <a href="https://mitglieder.gemuesekoop.de/" style="color:#176e38;">${msg("gkMembers")}</a> ·
                        <a href="https://www.gemuesekoop.de/impressum" style="color:#176e38;">${msg("gkLegal")}</a> ·
                        <a href="https://www.gemuesekoop.de/datenschutzerklarung" style="color:#176e38;">${msg("gkPrivacy")}</a>
                    </td>
                </tr>
            </table>
        </td>
    </tr>
</table>
</body>
</html>
</#macro>
