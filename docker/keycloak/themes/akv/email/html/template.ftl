<#-- Solawi Ackervielfalt: mail layout in the colours of www.solawi-ackervielfalt.de.
     Mail clients do not load web fonts reliably, so the text uses Fira Sans with fallbacks. -->
<#macro emailLayout realmName>
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>${realmName}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f1e7;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f4f1e7;">
    <tr>
        <td align="center" style="padding: 24px 12px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
                   style="max-width: 600px; background-color: #ffffff; border-radius: 10px; overflow: hidden;">
                <tr>
                    <td align="center" style="padding: 24px 24px 12px; background-color: #ffffff;">
                        <a href="https://www.solawi-ackervielfalt.de/">
                            <img src="https://www.solawi-ackervielfalt.de/wp-content/uploads/solawi-logo-400px-1.png"
                                 width="220" alt="Solawi Ackervielfalt"
                                 style="display: block; width: 220px; max-width: 100%; height: auto; border: 0;">
                        </a>
                    </td>
                </tr>
                <tr>
                    <td style="height: 4px; line-height: 4px; font-size: 1px; background-color: #bd4a55;">&nbsp;</td>
                </tr>
                <tr>
                    <td style="padding: 24px; font-family: 'Fira Sans', Helvetica, Arial, sans-serif; font-size: 16px; line-height: 26px; color: #000000;">
                        <p style="margin: 0 0 16px;">Hallo ${user.firstName!""}!</p>
                        <div style="margin: 0 0 16px;"><#nested></div>
                        <p style="margin: 0;">Liebe Grüße<br>${realmName}</p>
                    </td>
                </tr>
                <tr>
                    <td align="center"
                        style="padding: 16px 24px; background-color: #28476e; font-family: 'Fira Sans', Helvetica, Arial, sans-serif; font-size: 14px; line-height: 22px; color: #ffffff;">
                        <a href="https://www.solawi-ackervielfalt.de/" style="color: #ffffff; font-weight: 700; text-decoration: none;">www.solawi-ackervielfalt.de</a>
                    </td>
                </tr>
            </table>
        </td>
    </tr>
</table>
</body>
</html>
</#macro>
