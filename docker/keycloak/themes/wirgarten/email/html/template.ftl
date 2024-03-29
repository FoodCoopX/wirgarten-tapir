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
        font-family: 'Montserrat';
        font-style: normal;
        font-weight: 400;
        src: url('https://fonts.gstatic.com/s/montserrat/v25/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCtr6Ew9.woff') format('woff'), url('https://fonts.gstatic.com/s/montserrat/v25/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCtr6Ew7.woff2') format('woff2');
      }
      @font-face {
        font-family: 'Montserrat';
        font-style: normal;
        font-weight: 500;
        src: url('https://fonts.gstatic.com/s/montserrat/v25/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCtZ6Ew9.woff') format('woff'), url('https://fonts.gstatic.com/s/montserrat/v25/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCtZ6Ew7.woff2') format('woff2');
      }
      @font-face {
        font-family: 'Montserrat';
        font-style: normal;
        font-weight: 700;
        src: url('https://fonts.gstatic.com/s/montserrat/v25/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCuM70w9.woff') format('woff'), url('https://fonts.gstatic.com/s/montserrat/v25/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCuM70w7.woff2') format('woff2');
      }
      @font-face {
        font-family: 'Montserrat';
        font-style: normal;
        font-weight: 300;
        src: url('https://fonts.gstatic.com/s/montserrat/v25/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCs16Ew9.woff') format('woff'), url('https://fonts.gstatic.com/s/montserrat/v25/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCs16Ew7.woff2') format('woff2');
      }
      @font-face {
        font-family: 'Montserrat';
        font-style: normal;
        font-weight: 800;
        src: url('https://fonts.gstatic.com/s/montserrat/v25/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCvr70w9.woff') format('woff'), url('https://fonts.gstatic.com/s/montserrat/v25/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCvr70w7.woff2') format('woff2');
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

    div[style*="margin: 14px 0"],
    div[style*="margin: 16px 0"] {
      margin: 0 !important;
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
      mso-line-height-rule: exactly;
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

    .pc-gmail-fix {
      display: none;
      display: none !important;
    }

    @media screen and (min-width: 621px) {
      .pc-email-container {
        width: 620px !important;
      }
    }
    </style>
    <style type="text/css">
    @media screen and (max-width:620px) {
      .pc-sm-p-24-20-30 {
        padding: 24px 20px 30px !important
      }
      .pc-sm-mw-100pc {
        max-width: 100% !important
      }
      .pc-sm-p-25-10-15 {
        padding: 25px 10px 15px !important
      }
      .pc-sm-p-21-10-14 {
        padding: 21px 10px 14px !important
      }
      .pc-sm-h-20 {
        height: 20px !important
      }
    }
    </style>
    <style type="text/css">
    @media screen and (max-width:525px) {
      .pc-xs-p-15-10-20 {
        padding: 15px 10px 20px !important
      }
      .pc-xs-h-100 {
        height: 100px !important
      }
      .pc-xs-br-disabled br {
        display: none !important
      }
      .pc-xs-fs-30 {
        font-size: 30px !important
      }
      .pc-xs-lh-42 {
        line-height: 42px !important
      }
      .pc-xs-w-100pc {
        width: 100% !important
      }
      .pc-xs-p-10-0-0 {
        padding: 10px 0 0 !important
      }
      .pc-xs-p-15-0-5 {
        padding: 15px 0 5px !important
      }
      .pc-xs-p-5-0 {
        padding: 5px 0 !important
      }
    }
    </style>
    <!--[if mso]>
    <style type="text/css">
        .pc-fb-font {
            font-family: Helvetica, Arial, sans-serif !important;
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
<body style="width: 100% !important; margin: 0; padding: 0; mso-line-height-rule: exactly; -webkit-font-smoothing: antialiased; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; background-color: #f4f4f4"
      class="">
<div style="display: none !important; visibility: hidden; opacity: 0; overflow: hidden; mso-hide: all; height: 0; width: 0; max-height: 0; max-width: 0; font-size: 1px; line-height: 1px; color: #151515;"><#nested></div>
<div style="display: none !important; visibility: hidden; opacity: 0; overflow: hidden; mso-hide: all; height: 0; width: 0; max-height: 0; max-width: 0; font-size: 1px; line-height: 1px;">
    ‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;
</div>
<table class="pc-email-body" width="100%" bgcolor="#f4f4f4" border="0" cellpadding="0" cellspacing="0"
       role="presentation" style="table-layout: fixed;">
    <tbody>
    <tr>
        <td class="pc-email-body-inner" align="center" valign="top">
            <!--[if gte mso 9]>
            <v:background xmlns:v="urn:schemas-microsoft-com:vml" fill="t">
                <v:fill type="tile" src="" color="#f4f4f4"/>
            </v:background>
            <![endif]-->
            <!--[if (gte mso 9)|(IE)]>
            <table width="620" align="center" border="0" cellspacing="0" cellpadding="0" role="presentation">
                <tr>
                    <td width="620" align="center" valign="top"><![endif]-->
            <table class="pc-email-container" width="100%" align="center" border="0" cellpadding="0" cellspacing="0"
                   role="presentation" style="margin: 0 auto; max-width: 620px;">
                <tbody>
                <tr>
                    <td align="left" valign="top" style="padding: 0 10px;">
                        <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation">
                            <tbody>
                            <tr>
                                <td height="20" style="font-size: 1px; line-height: 1px;">&nbsp;</td>
                            </tr>
                            </tbody>
                        </table>
                        <table width="100%" border="0" cellspacing="0" cellpadding="0" role="presentation">
                            <tbody>
                            <tr>
                                <td valign="top">
                                    <!-- BEGIN MODULE: Header 1 -->
                                    <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation">
                                        <tbody>
                                        <tr>
                                            <td bgcolor="#184b23" valign="top"
                                                style="background-color: #184b23; background-repeat: no-repeat; background-position: center; background-size: cover; background-image: url('https://lueneburg.wirgarten.com/wp-content/uploads/sites/4/2023/03/Newsletter-Wir-Garten-Lueneburg-xbq.jpg')"
                                                background="https://lueneburg.wirgarten.com/wp-content/uploads/sites/4/2023/03/Newsletter-Wir-Garten-Lueneburg-xbq.jpg">
                                                <!--[if gte mso 9]>
                          <v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false" style="width: 600px;">
                              <v:fill type="frame" src="https://lueneburg.wirgarten.com/wp-content/uploads/sites/4/2023/03/Newsletter-Wir-Garten-Lueneburg-xbq.jpg" color="#184b23"></v:fill>
                              <v:textbox style="mso-fit-shape-to-text: true;" inset="0,0,0,0">
                                  <div style="font-size: 0; line-height: 0;">
                                      <table width="600" border="0" cellpadding="0" cellspacing="0" role="presentation" align="center">
                                          <tr>
                                              <td style="font-size: 14px; line-height: 1.5;" valign="top">
                                                  <table width="100%" border="0" cellspacing="0" cellpadding="0" role="presentation">
                                                      <tr>
                                                          <td colspan="3" height="24" style="line-height: 1px; font-size: 1px;">&nbsp;</td>
                                                      </tr>
                                                      <tr>
                                                          <td width="30" valign="top" style="line-height: 1px; font-size: 1px;">&nbsp;</td>
                                                          <td valign="top" align="left">
                          <![endif]-->
                                                <!--[if !gte mso 9]><!-->
                                                <table width="100%" border="0" cellspacing="0" cellpadding="0"
                                                       role="presentation">
                                                    <tbody>
                                                    <tr>
                                                        <td class="pc-sm-p-24-20-30 pc-xs-p-15-10-20" valign="top"
                                                            style="padding: 24px 30px 40px;">
                                                            <!--<![endif]-->
                                                            <table width="100%" border="0" cellpadding="0"
                                                                   cellspacing="0" role="presentation">
                                                                <tbody>
                                                                <tr>
                                                                    <td valign="top" style="padding: 10px;">
                                                                        <a href="https://lueneburg.wirgarten.com/"
                                                                           style="text-decoration: none;"><img
                                                                                src="https://lueneburg.wirgarten.com/wp-content/uploads/sites/4/2023/03/150616_wir_garten_logo_lueneburg-SUr.png"
                                                                                width="100" height="100" alt=""
                                                                                style="max-width: 100%; height: auto; border: 0; line-height: 100%; outline: 0; -ms-interpolation-mode: bicubic; font-size: 14px; color: #ffffff;"></a>
                                                                    </td>
                                                                </tr>
                                                                <tr>
                                                                    <td class="pc-xs-h-100" height="110"
                                                                        style="line-height: 1px; font-size: 1px">&nbsp;
                                                                    </td>
                                                                </tr>
                                                                <tr>
                                                                    <td class="pc-xs-fs-30 pc-xs-lh-42 pc-fb-font"
                                                                        valign="top"
                                                                        style="padding: 13px 10px 0; letter-spacing: -0.7px; line-height: 46px; font-family: 'Montserrat', Helvetica, Arial, sans-serif; font-size: 38px; font-weight: 800; color: #ffffff">Mehr als nur Gemüse
                                                                    </td>
                                                                </tr>
                                                                </tbody>
                                                            </table>
                                                            <!--[if !gte mso 9]><!-->
                                                        </td>
                                                    </tr>
                                                    </tbody>
                                                </table>
                                                <!--<![endif]-->
                                                <!--[if gte mso 9]>
                                                          </td>
                                                          <td width="30" style="line-height: 1px; font-size: 1px;" valign="top">&nbsp;</td>
                                                      </tr>
                                                      <tr>
                                                          <td colspan="3" height="40" style="line-height: 1px; font-size: 1px;">&nbsp;</td>
                                                      </tr>
                                                  </table>
                                              </td>
                                          </tr>
                                      </table>
                                  </div>
                              </v:textbox>
                          </v:rect>
                          <![endif]-->
                                            </td>
                                        </tr>
                                        </tbody>
                                    </table>
                                    <!-- END MODULE: Header 1 -->
                                    <!-- BEGIN MODULE: Content 2 -->
                                    <table border="0" cellpadding="0" cellspacing="0" width="100%" role="presentation">
                                        <tbody>
                                        <tr>
                                            <td class="" valign="top" bgcolor="#ffffff"
                                                style="padding: 30px 20px; background-color: #ffffff"
                                                pc-default-class="pc-sm-p-25-10-15 pc-xs-p-15-0-5"
                                                pc-default-padding="30px 20px 20px">
                                                <table border="0" cellpadding="0" cellspacing="0" width="100%"
                                                       role="presentation">
                                                    <tbody>
                                                    <tr>
                                                        <td valign="top" style="padding: 0 20px;">
                                                            <table border="0" cellpadding="0" cellspacing="0"
                                                                   width="100%" role="presentation">
                                                                <tbody>
                                                                <tr>
                                                                    <td class="pc-fb-font" valign="top"
                                                                        style="padding: 10px 0 0; font-family: 'Montserrat', Helvetica, Arial, sans-serif; font-size: 24px; font-weight: 700; line-height: 34px; letter-spacing: -0.4px; color: #151515"></td>
                                                                </tr>
                                                                </tbody>
                                                            </table>
                                                        </td>
                                                    </tr>
                                                    </tbody>
                                                    <tbody>
                                                    <tr>
                                                        <td class="pc-fb-font" valign="top"
                                                            style="font-family: 'Montserrat', Helvetica, Arial, sans-serif; padding: 10px 20px 0; line-height: 28px; font-size: 18px; font-weight: 300; letter-spacing: -0.2px; color: #000000">
                                                            <div>Hallo ${user.firstName}!<br/><br/>
                                                            <#nested><br/><br/>
                                                            Liebe Grüße aus deinem ${realmName}</div>
                                                        </td>
                                                    </tr>
                                                    <tr>
                                                        <td height="4"
                                                            style="font-size: 1px; line-height: 1px;">&nbsp;
                                                        </td>
                                                    </tr>
                                                    </tbody>
                                                </table>
                                            </td>
                                        </tr>
                                        </tbody>
                                    </table>
                                    <!-- END MODULE: Content 2 -->
                                    <!-- BEGIN MODULE: Footer 1 -->
                                    <table border="0" cellpadding="0" cellspacing="0" width="100%" role="presentation">
                                        <tbody>
                                        <tr>
                                            <td class="pc-sm-p-21-10-14 pc-xs-p-5-0"
                                                style="padding: 21px 20px 14px 20px; background-color: #184b23"
                                                valign="top" bgcolor="#184b23" role="presentation">
                                                <table border="0" cellpadding="0" cellspacing="0" width="100%"
                                                       role="presentation">
                                                    <tbody>
                                                    <tr>
                                                        <td style="font-size: 0;" valign="top">
                                                            <!--[if (gte mso 9)|(IE)]>
                                                            <table width="100%" border="0" cellspacing="0"
                                                                   cellpadding="0" role="presentation">
                                                                <tr>
                                                                    <td width="280" valign="top"><![endif]-->
                                                            <div class="pc-sm-mw-100pc"
                                                                 style="display: inline-block; width: 100%; max-width: 280px; vertical-align: top;">
                                                                <table border="0" cellpadding="0" cellspacing="0"
                                                                       width="100%" role="presentation">
                                                                    <tbody>
                                                                    <tr>
                                                                        <td style="padding: 20px;" valign="top">
                                                                            <table border="0" cellpadding="0"
                                                                                   cellspacing="0" width="100%"
                                                                                   role="presentation">
                                                                                <tbody>
                                                                                <tr>
                                                                                    <td class="pc-fb-font"
                                                                                        style="font-family: 'Montserrat', Helvetica, Arial, sans-serif; font-size: 14px; line-height: 20px; letter-spacing: -0.2px; color: #ffffff"
                                                                                        valign="top">
                                                                                        <h3>Interessante Links</h3>
                                                                                        <p><a style="color: #f49633;"
                                                                                              href="https://lueneburg.wirgarten.com/genossenschaft/#team">Das Wir Garten Team</a>
                                                                                        </p>
                                                                                        <p><a style="color: #f49633;"
                                                                                              href="https://lueneburg.wirgarten.com/wir/">Veranstaltungen</a>
                                                                                        </p>
                                                                                        <p><a style="color: #f49633;"
                                                                                              href="https://lueneburg.wirgarten.com/aktuelles/">Aktuelles</a>
                                                                                        </p>
                                                                                        <p>&nbsp;</p>
                                                                                        <h3>Rechtliches</h3>
                                                                                        <p><a style="color: #f49633;"
                                                                                              href="https://lueneburg.wirgarten.com/impressum/">Impressum</a>
                                                                                        </p>
                                                                                        <p><a style="color: #f49633;"
                                                                                              href="https://lueneburg.wirgarten.com/datenschutzerklaerung/">Datenschutz</a>
                                                                                        </p>
                                                                                    </td>
                                                                                </tr>
                                                                                <tr>
                                                                                    <td class="pc-sm-h-20" height="56"
                                                                                        style="line-height: 1px; font-size: 1px;">&nbsp;
                                                                                    </td>
                                                                                </tr>
                                                                                </tbody>
                                                                                <tbody>
                                                                                <tr>
                                                                                    <td style="font-family: Arial, sans-serif; font-size: 19px;"
                                                                                        valign="top">
                                                                                        <a href="https://www.instagram.com/wirgarten_lueneburg/"
                                                                                           style="text-decoration: none;"><img
                                                                                                src="https://lueneburg.wirgarten.com/wp-content/uploads/sites/4/2023/03/instagram-icon-white@2x-ph2.png"
                                                                                                width="20" height="20"
                                                                                                alt=""
                                                                                                style="border: 0; line-height: 100%; outline: 0; -ms-interpolation-mode: bicubic; color: #ffffff;"></a><span>&nbsp;&nbsp;</span><a
                                                                                            href="https://www.facebook.com/lueneburg.WirGarten"
                                                                                            style="text-decoration: none;"><img
                                                                                            src="https://lueneburg.wirgarten.com/wp-content/uploads/sites/4/2023/03/facebook-icon-white@2x-G7w.png"
                                                                                            width="10.2422" height="20"
                                                                                            alt=""
                                                                                            style="border: 0; line-height: 100%; outline: 0; -ms-interpolation-mode: bicubic; color: #ffffff;"></a><span>&nbsp;&nbsp;</span><a
                                                                                            href="https://www.youtube.com/channel/UC00NDIWV1-o2pQHMjvA7Zjg"
                                                                                            style="text-decoration: none;"><img
                                                                                            src="https://lueneburg.wirgarten.com/wp-content/uploads/sites/4/2023/03/Youtube-icon-white@2x-paZ.png"
                                                                                            width="28.2891" height="20"
                                                                                            alt=""
                                                                                            style="border: 0; line-height: 100%; outline: 0; -ms-interpolation-mode: bicubic; color: #ffffff;"></a>
                                                                                    </td>
                                                                                </tr>
                                                                                </tbody>
                                                                            </table>
                                                                        </td>
                                                                    </tr>
                                                                    </tbody>
                                                                </table>
                                                            </div>
                                                            <!--[if (gte mso 9)|(IE)]></td>
                                                        <td width="280" valign="top"><![endif]-->
                                                            <div class="pc-sm-mw-100pc"
                                                                 style="display: inline-block; width: 100%; max-width: 280px; vertical-align: top;">
                                                                <table border="0" cellpadding="0" cellspacing="0"
                                                                       width="100%" role="presentation">
                                                                    <tbody>
                                                                    <tr>
                                                                        <td style="padding: 20px;" valign="top">
                                                                            <table border="0" cellpadding="0"
                                                                                   cellspacing="0" width="100%"
                                                                                   role="presentation">
                                                                                <tbody>
                                                                                <tr>
                                                                                    <td class="pc-fb-font"
                                                                                        style="font-family: 'Montserrat', Helvetica, Arial, sans-serif; font-size: 14px; line-height: 20px; letter-spacing: -0.2px; color: #ffffff"
                                                                                        valign="top">
                                                                                        <h3>Kontakt</h3>
                                                                                        WirGarten Lüneburg eG<br>Vögelser Straße 25<br>21339 Lüneburg-Ochtmissen<br><br><strong>Tel.:</strong> 0176 34 45 81 48<br><br><strong>E-Mail:</strong>&nbsp;lueneburg@wirgarten.com
                                                                                    </td>
                                                                                </tr>
                                                                                <tr>
                                                                                    <td class="pc-sm-h-20" height="45"
                                                                                        style="line-height: 1px; font-size: 1px;">&nbsp;
                                                                                    </td>
                                                                                </tr>
                                                                                </tbody>
                                                                                <tbody>
                                                                                <tr>
                                                                                    <td class="pc-fb-font"
                                                                                        style="font-family: 'Montserrat', Helvetica, Arial, sans-serif; font-size: 18px; font-weight: 500; line-height: 24px; letter-spacing: -0.2px"
                                                                                        valign="top">
                                                                                        <a href="https://mitglieder.lueneburg.wirgarten.com"
                                                                                           style="text-decoration: none; color: #f49633; font-size: 16px">Link zum Mitgliederbereich</a>
                                                                                    </td>
                                                                                </tr>
                                                                                <tr>
                                                                                    <td height="9"
                                                                                        style="line-height: 1px; font-size: 1px;">&nbsp;
                                                                                    </td>
                                                                                </tr>
                                                                                </tbody>
                                                                                <tbody>
                                                                                </tbody>
                                                                            </table>
                                                                        </td>
                                                                    </tr>
                                                                    </tbody>
                                                                </table>
                                                            </div>
                                                            <!--[if (gte mso 9)|(IE)]></td></tr></table><![endif]-->
                                                        </td>
                                                    </tr>
                                                    </tbody>
                                                </table>
                                            </td>
                                        </tr>
                                        </tbody>
                                    </table>
                                    <!-- END MODULE: Footer 1 -->
                                </td>
                            </tr>
                            </tbody>
                        </table>
                        <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation">
                            <tbody>
                            <tr>
                                <td height="20" style="font-size: 1px; line-height: 1px;">&nbsp;</td>
                            </tr>
                            </tbody>
                        </table>
                    </td>
                </tr>
                </tbody>
            </table>
            <!--[if (gte mso 9)|(IE)]></td></tr></table><![endif]-->
        </td>
    </tr>
    </tbody>
</table>
<!-- Fix for Gmail on iOS -->
<div class="pc-gmail-fix"
     style="white-space: nowrap; font: 15px courier; line-height: 0;">&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
</div>
</body>
</html>
</#macro>