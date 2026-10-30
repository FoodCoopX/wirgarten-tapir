<#macro emailLayout realmName>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml"
      xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <!--[if !mso]><!-->
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <!--<![endif]-->
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="format-detection" content="telephone=no">
    <meta name="x-apple-disable-message-reformatting">
    <title></title>
    <style type="text/css">
    @media screen {
      @font-face {
        font-family: 'Nunito';
        font-style: normal;
        font-weight: 400;
        src: url('http://static.solawi-vierlande.de/fonts/nunito-regular.ttf') format('truetype');
      }
      @font-face {
        font-family: 'Nunito';
        font-style: normal;
        font-weight: 600;
        src: url('http://static.solawi-vierlande.de/fonts/nunito-semibold.ttf') format('truetype');
      }
      @font-face {
        font-family: 'Nunito';
        font-style: normal;
        font-weight: 700;
        src: url('http://static.solawi-vierlande.de/fonts/nunito-bold.ttf') format('truetype');
      }
    }
    </style>
    <style type="text/css">
    #outlook a {
      padding: 0;
    }

    .ReadMsgBody,
    .ExternalClass {
      width: 100%;
    }

    .ExternalClass,
    .ExternalClass p,
    .ExternalClass td,
    .ExternalClass div,
    .ExternalClass span,
    .ExternalClass font {
      line-height: 100%;
    }

    table,
    td {
      mso-table-lspace: 0;
      mso-table-rspace: 0;
    }

    table,
    tr,
    td {
      border-collapse: collapse;
    }

    body,
    td,
    th,
    p,
    div,
    li,
    a,
    span {
      -webkit-text-size-adjust: 100%;
      -ms-text-size-adjust: 100%;
    }

    img {
      border: 0;
      outline: none;
      line-height: 100%;
      text-decoration: none;
      -ms-interpolation-mode: bicubic;
    }

    a[x-apple-data-detectors] {
      color: inherit !important;
      text-decoration: none !important;
    }

    body {
      margin: 0;
      padding: 0;
      width: 100% !important;
      -webkit-font-smoothing: antialiased;
    }

    @media screen and (max-width: 620px) {
      .pc-sm-pad {
        padding-left: 12px !important;
        padding-right: 12px !important;
      }
      .pc-sm-pad-inner {
        padding-left: 20px !important;
        padding-right: 20px !important;
      }
      .pc-sm-col {
        display: block !important;
        width: 100% !important;
        max-width: 100% !important;
      }
      .pc-sm-logo {
        width: 100% !important;
        height: auto !important;
      }
    }
    </style>
    <!--[if mso]>
    <style type="text/css">
        .pc-fb-font {
            font-family: Verdana, Arial, sans-serif !important;
        }
    </style>
    <![endif]-->
    <!--[if gte mso 9]>
    <xml>
        <o:OfficeDocumentSettings>
            <o:AllowPNG/>
            <o:PixelsPerInch>96</o:PixelsPerInch>
        </o:OfficeDocumentSettings>
    </xml><![endif]-->
</head>
<body style="width: 100% !important; margin: 0; padding: 0; -webkit-font-smoothing: antialiased; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; background-color: #f8f8f8;">
<div style="display: none !important; visibility: hidden; opacity: 0; overflow: hidden; mso-hide: all; height: 0; width: 0; max-height: 0; max-width: 0; font-size: 1px; line-height: 1px; color: #f8f8f8;"><#nested></div>
<table width="100%" bgcolor="#f8f8f8" border="0" cellpadding="0" cellspacing="0" role="presentation"
       style="table-layout: fixed; background-color: #f8f8f8;">
    <tbody>
    <tr>
        <td class="pc-sm-pad" align="center" valign="top" style="padding: 24px 12px;">
            <table class="pc-email-container" width="100%" align="center" border="0" cellpadding="0" cellspacing="0"
                   role="presentation" style="margin: 0 auto; max-width: 576px;">
                <tbody>
                <!-- BEGIN MODULE: Content -->
                <tr>
                    <td style="padding-bottom: 12px;">
                        <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation"
                               style="background-color: #ffffff; border: 1px solid #e5e5e5; border-radius: 12px;">
                            <tbody>
                            <tr>
                                <td class="pc-fb-font pc-sm-pad-inner" align="left" valign="top"
                                    style="padding: 22px 24px; font-family: 'Nunito', Verdana, Geneva, 'Helvetica Neue', 'Segoe UI', Helvetica, sans-serif; font-size: 15px; line-height: 1.6; color: #000000;">
                                    <div style="text-align: center; padding-bottom: 18px;">
                                        <a href="https://www.solawi-vierlande.de" style="text-decoration: none;">
                                            <img class="pc-sm-logo"
                                                 src="https://static.solawi-vierlande.de/Solawi-Logo_Q_mitMoehre_frei.png"
                                                 width="528" alt="Solidarische Landwirtschaft Vierlande e. V."
                                                 style="display: block; width: 528px; max-width: 100%; height: auto; border: 0; line-height: 100%; outline: 0; -ms-interpolation-mode: bicubic;">
                                        </a>
                                    </div>
                                    <div>Hallo ${user.firstName}!<br/><br/><#nested><br/><br/>Liebe Grüße aus deinem ${realmName}</div>
                                </td>
                            </tr>
                            </tbody>
                        </table>
                    </td>
                </tr>
                <!-- END MODULE: Content -->
                <!-- BEGIN MODULE: Footer -->
                <tr>
                    <td>
                        <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation"
                               style="background-color: #ffffff; border: 1px solid #e5e5e5; border-radius: 12px;">
                            <tbody>
                            <tr>
                                <td class="pc-fb-font pc-sm-pad-inner" align="center" valign="top"
                                    style="padding: 22px 24px; font-family: 'Nunito', Verdana, Geneva, 'Helvetica Neue', 'Segoe UI', Helvetica, sans-serif; font-size: 15px; line-height: 1.6; color: #000000;">
                                    <div style="font-size: 16px; line-height: 1.5; padding-bottom: 10px;">&#127987;&#65039;&#8205;&#127752; &#127987;&#65039;&#8205;&#9895;&#65039; &#128420; &#10084;&#65039; &#129365; &#129364; &#127813; &#129382; &#128154;</div>
                                    <div style="padding-bottom: 10px;"><strong style="color: #2b3050;">Solidarische Landwirtschaft Vierlande e. V.</strong> | &copy; ${.now?string('yyyy')}</div>
                                    <div style="padding-bottom: 10px;">
                                        <a href="https://www.solawi-vierlande.de/impressum"
                                           style="color: #30a89f; text-decoration: underline; font-weight: 700;">Impressum</a>
                                        &nbsp;|&nbsp;
                                        <a href="https://www.solawi-vierlande.de/datenschutz"
                                           style="color: #30a89f; text-decoration: underline; font-weight: 700;">Datenschutz</a>
                                    </div>
                                    <div style="font-size: 11px; line-height: 1.6; color: #4a4a4a; padding-bottom: 14px;">Dieses Projekt wird aus Mitteln des Bezirksamtes Bergedorf gefördert</div>
                                    <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation">
                                        <tbody>
                                        <tr>
                                            <td class="pc-sm-col" width="50%" align="center" valign="middle" style="padding: 8px;">
                                                <a href="https://www.solidarische-landwirtschaft.org/" style="text-decoration: none;">
                                                    <img src="https://www.solawi-vierlande.de/user/pages/tecart-media/logos/logo-solawi-120.png"
                                                         width="120" alt="Netzwerk Solidarische Landwirtschaft"
                                                         style="display: block; width: 120px; max-width: 100%; height: auto; border: 0; line-height: 100%; outline: 0; -ms-interpolation-mode: bicubic;">
                                                </a>
                                            </td>
                                            <td class="pc-sm-col" width="50%" align="center" valign="middle" style="padding: 8px;">
                                                <a href="https://abcert-web.de/biokonv3/WebBescheinigung.nsf/xpUnternehmen.xsp?documentId=B28C2D1BC9B29535C12581ED00737929"
                                                   style="text-decoration: none;">
                                                    <img src="https://www.solawi-vierlande.de/user/pages//tecart-media/logos/bioland-de-%C3%B6ko-006-120.png"
                                                         width="120" alt="DE-ÖKO-006 Zertifiziert"
                                                         style="display: block; width: 120px; max-width: 100%; height: auto; border: 0; line-height: 100%; outline: 0; -ms-interpolation-mode: bicubic;">
                                                </a>
                                            </td>
                                        </tr>
                                        </tbody>
                                    </table>
                                </td>
                            </tr>
                            </tbody>
                        </table>
                    </td>
                </tr>
                <!-- END MODULE: Footer -->
                </tbody>
            </table>
        </td>
    </tr>
    </tbody>
</table>
</body>
</html>
</#macro>
