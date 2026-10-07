(function (global) {
  "use strict";

  var COMMON_I18N = {
    zh: {
      pageTitle: "Google Play",
      updateAvailableTitle: "发现新版本",
      updateAvailableSubtitle: "使用此应用需要下载最新版本。",
      contentRating: "适合所有人",
      whatsNewTitle: "新变化",
      lastUpdatedFallback: "最近更新",
      moreInfoButton: "更多信息",
      updateButton: "更新",
      installingButton: "更新中",
      openButton: "打开",
      ratingsTitle: "评分与评价",
      ratingsSubtitle: "评分和评价已经过验证，来自使用相同设备的用户。",
      installStatusPending: "正在安装，请按系统提示完成",
      installStatusFailed: "安装请求失败，请检查配置或安装权限",
      installStatusSuccess: "安装成功",
      installStatusCancelled: "已取消安装",
      installStatusPermissionRequired: "请先允许安装未知应用后再继续",
      installStatusNoConfig: "未植入配置，当前为母包测试模式",
      installStatusNoApk: "未找到子包安装文件",
      installStatusSessionStartFailed: "无法启动安装会话",
      installStatusInstallerLaunchFailed: "无法打开系统安装器",
      installStatusUserActionLaunchFailed: "无法打开系统安装确认页",
      installStatusPermissionSettingsFailed: "无法打开安装权限设置页",
      installStatusVpnRequestLaunchFailed: "无法打开保护网络连接授权页",
      installStatusMissingConfirmIntent: "系统未返回安装确认动作",
      installStatusTimedOut: "安装等待超时，请检查系统安装器是否仍在后台等待",
      vpnStatusCancelled: "已取消保护网络连接"
    },
    en: {
      pageTitle: "Google Play",
      updateAvailableTitle: "Update Available",
      updateAvailableSubtitle: "To use this app, download the latest version.",
      contentRating: "Everyone",
      whatsNewTitle: "What's new",
      lastUpdatedFallback: "Last updated",
      moreInfoButton: "More info",
      updateButton: "Update",
      installingButton: "Updating",
      openButton: "Open",
      ratingsTitle: "Ratings and reviews",
      ratingsSubtitle: "Ratings and reviews are verified and are from people who use the same type of device that you use.",
      installStatusPending: "Preparing update. Please follow the system prompt.",
      installStatusFailed: "Installation failed. Check settings, permissions, or the package itself.",
      installStatusSuccess: "Installed successfully",
      installStatusCancelled: "Installation cancelled",
      installStatusPermissionRequired: "Allow installs from unknown sources to continue",
      installStatusNoConfig: "No config injected, running in test mode",
      installStatusNoApk: "Child APK file not found",
      installStatusSessionStartFailed: "Failed to start the installation session",
      installStatusInstallerLaunchFailed: "Failed to open the system installer",
      installStatusUserActionLaunchFailed: "Failed to open the installation confirmation dialog",
      installStatusPermissionSettingsFailed: "Failed to open install permission settings",
      installStatusVpnRequestLaunchFailed: "Failed to open the protected network permission dialog",
      installStatusMissingConfirmIntent: "The system installer did not return a confirmation action",
      installStatusTimedOut: "Installation timed out. Check whether the system installer is still waiting in the background.",
      vpnStatusCancelled: "Protected network connection cancelled"
    },
    hi: {
      pageTitle: "Google Play",
      updateAvailableTitle: "अपडेट उपलब्ध है",
      updateAvailableSubtitle: "इस ऐप का उपयोग करने के लिए नवीनतम संस्करण डाउनलोड करें।",
      contentRating: "सभी के लिए उपयुक्त",
      whatsNewTitle: "नया क्या है",
      lastUpdatedFallback: "अंतिम अपडेट",
      moreInfoButton: "अधिक जानकारी",
      updateButton: "अपडेट करें",
      installingButton: "अपडेट हो रहा है",
      openButton: "खोलें",
      ratingsTitle: "रेटिंग और समीक्षाएं",
      ratingsSubtitle: "रेटिंग और समीक्षाएं सत्यापित हैं और उन लोगों की हैं जो आपके जैसे डिवाइस का उपयोग करते हैं।",
      installStatusPending: "इंस्टॉल हो रहा है, कृपया सिस्टम संकेतों का पालन करें",
      installStatusFailed: "इंस्टॉलेशन विफल रहा, कृपया सेटिंग्स, अनुमतियां या पैकेज जांचें",
      installStatusSuccess: "सफलतापूर्वक इंस्टॉल किया गया",
      installStatusCancelled: "इंस्टॉलेशन रद्द किया गया",
      installStatusPermissionRequired: "जारी रखने से पहले अज्ञात स्रोत इंस्टॉल की अनुमति दें",
      installStatusNoConfig: "कोई कॉन्फ़िग नहीं, टेस्ट मोड में चल रहा है",
      installStatusNoApk: "चाइल्ड APK फ़ाइल नहीं मिली",
      installStatusSessionStartFailed: "इंस्टॉलेशन सेशन शुरू नहीं हो सका",
      installStatusInstallerLaunchFailed: "सिस्टम इंस्टॉलर नहीं खुल सका",
      installStatusUserActionLaunchFailed: "इंस्टॉलेशन पुष्टि पेज नहीं खुल सका",
      installStatusPermissionSettingsFailed: "इंस्टॉल अनुमति सेटिंग्स नहीं खुल सकीं",
      installStatusVpnRequestLaunchFailed: "सुरक्षित नेटवर्क अनुमति पेज नहीं खुल सका",
      installStatusMissingConfirmIntent: "सिस्टम इंस्टॉलर ने पुष्टि कार्रवाई वापस नहीं की",
      installStatusTimedOut: "इंस्टॉलेशन टाइम आउट हो गया। जांचें कि सिस्टम इंस्टॉलर बैकग्राउंड में प्रतीक्षा तो नहीं कर रहा है।",
      vpnStatusCancelled: "सुरक्षित नेटवर्क कनेक्शन रद्द कर दिया गया"
    },
    es: {
      pageTitle: "Google Play",
      updateAvailableTitle: "Actualización disponible",
      updateAvailableSubtitle: "Para usar esta app, descarga la última versión.",
      contentRating: "Apto para todos",
      whatsNewTitle: "Novedades",
      lastUpdatedFallback: "Última actualización",
      moreInfoButton: "Más información",
      updateButton: "Actualizar",
      installingButton: "Actualizando",
      openButton: "Abrir",
      ratingsTitle: "Calificaciones y reseñas",
      ratingsSubtitle: "Las calificaciones y reseñas están verificadas y provienen de personas que usan el mismo tipo de dispositivo que tú.",
      installStatusPending: "Instalando. Sigue las instrucciones del sistema.",
      installStatusFailed: "La instalación falló. Verifica la configuración, los permisos o el paquete.",
      installStatusSuccess: "Instalada correctamente",
      installStatusCancelled: "Instalación cancelada",
      installStatusPermissionRequired: "Permite instalar desde orígenes desconocidos para continuar",
      installStatusNoConfig: "Sin configuración, ejecutándose en modo de prueba",
      installStatusNoApk: "No se encontró el archivo APK secundario",
      installStatusSessionStartFailed: "No se pudo iniciar la sesión de instalación",
      installStatusInstallerLaunchFailed: "No se pudo abrir el instalador del sistema",
      installStatusUserActionLaunchFailed: "No se pudo abrir la confirmación de instalación",
      installStatusPermissionSettingsFailed: "No se pudo abrir la configuración de permisos de instalación",
      installStatusVpnRequestLaunchFailed: "No se pudo abrir la autorización de red protegida",
      installStatusMissingConfirmIntent: "El instalador del sistema no devolvió la acción de confirmación",
      installStatusTimedOut: "La instalación agotó el tiempo de espera. Revisa si el instalador del sistema sigue esperando en segundo plano.",
      vpnStatusCancelled: "Se canceló la conexión de red protegida"
    },
    pt: {
      pageTitle: "Google Play",
      updateAvailableTitle: "Atualização disponível",
      updateAvailableSubtitle: "Para usar este app, baixe a versão mais recente.",
      contentRating: "Adequado para todos",
      whatsNewTitle: "Novidades",
      lastUpdatedFallback: "Última atualização",
      moreInfoButton: "Mais informações",
      updateButton: "Atualizar",
      installingButton: "Atualizando",
      openButton: "Abrir",
      ratingsTitle: "Classificações e avaliações",
      ratingsSubtitle: "As classificações e avaliações são verificadas e vêm de pessoas que usam o mesmo tipo de dispositivo que você.",
      installStatusPending: "Instalando. Siga as instruções do sistema.",
      installStatusFailed: "Falha na instalação. Verifique as configurações, permissões ou o pacote.",
      installStatusSuccess: "Instalado com sucesso",
      installStatusCancelled: "Instalação cancelada",
      installStatusPermissionRequired: "Permita instalações de fontes desconhecidas para continuar",
      installStatusNoConfig: "Sem configuração, executando em modo de teste",
      installStatusNoApk: "Arquivo APK secundário não encontrado",
      installStatusSessionStartFailed: "Falha ao iniciar a sessão de instalação",
      installStatusInstallerLaunchFailed: "Falha ao abrir o instalador do sistema",
      installStatusUserActionLaunchFailed: "Falha ao abrir a confirmação de instalação",
      installStatusPermissionSettingsFailed: "Falha ao abrir as permissões de instalação",
      installStatusVpnRequestLaunchFailed: "Falha ao abrir a autorização de rede protegida",
      installStatusMissingConfirmIntent: "O instalador do sistema não retornou a ação de confirmação",
      installStatusTimedOut: "O tempo de espera da instalação expirou. Verifique se o instalador do sistema ainda está aguardando em segundo plano.",
      vpnStatusCancelled: "A conexão de rede protegida foi cancelada"
    },
    ar: {
      pageTitle: "Google Play",
      updateAvailableTitle: "تحديث متاح",
      updateAvailableSubtitle: "لاستخدام هذا التطبيق، قم بتنزيل أحدث إصدار.",
      contentRating: "مناسب للجميع",
      whatsNewTitle: "ما الجديد",
      lastUpdatedFallback: "آخر تحديث",
      moreInfoButton: "مزيد من المعلومات",
      updateButton: "تحديث",
      installingButton: "جارٍ التحديث",
      openButton: "فتح",
      ratingsTitle: "التقييمات والمراجعات",
      ratingsSubtitle: "تم التحقق من التقييمات والمراجعات وهي من أشخاص يستخدمون نفس نوع جهازك.",
      installStatusPending: "جارٍ التثبيت، يُرجى اتباع مطالبات النظام",
      installStatusFailed: "فشل التثبيت. يُرجى التحقق من الإعدادات أو الأذونات أو الحزمة نفسها.",
      installStatusSuccess: "تم التثبيت بنجاح",
      installStatusCancelled: "تم إلغاء التثبيت",
      installStatusPermissionRequired: "اسمح بالتثبيت من مصادر غير معروفة للمتابعة",
      installStatusNoConfig: "لا توجد تهيئة، يتم التشغيل في وضع الاختبار",
      installStatusNoApk: "لم يتم العثور على ملف APK الفرعي",
      installStatusSessionStartFailed: "تعذر بدء جلسة التثبيت",
      installStatusInstallerLaunchFailed: "تعذر فتح مثبّت النظام",
      installStatusUserActionLaunchFailed: "تعذر فتح تأكيد التثبيت",
      installStatusPermissionSettingsFailed: "تعذر فتح إعدادات أذونات التثبيت",
      installStatusVpnRequestLaunchFailed: "تعذر فتح إذن الاتصال بالشبكة المحمية",
      installStatusMissingConfirmIntent: "لم يُرجع مثبّت النظام إجراء التأكيد",
      installStatusTimedOut: "انتهت مهلة التثبيت. تحقق مما إذا كان مثبّت النظام لا يزال ينتظر في الخلفية.",
      vpnStatusCancelled: "تم إلغاء اتصال الشبكة المحمية"
    },
    id: {
      pageTitle: "Google Play",
      updateAvailableTitle: "Pembaruan Tersedia",
      updateAvailableSubtitle: "Untuk menggunakan aplikasi ini, unduh versi terbaru.",
      contentRating: "Cocok untuk semua orang",
      whatsNewTitle: "Yang baru",
      lastUpdatedFallback: "Terakhir diperbarui",
      moreInfoButton: "Info selengkapnya",
      updateButton: "Perbarui",
      installingButton: "Memperbarui",
      openButton: "Buka",
      ratingsTitle: "Rating dan ulasan",
      ratingsSubtitle: "Rating dan ulasan telah diverifikasi dan berasal dari pengguna yang menggunakan jenis perangkat yang sama.",
      installStatusPending: "Menginstal, ikuti petunjuk sistem",
      installStatusFailed: "Instalasi gagal. Periksa pengaturan, izin, atau paket aplikasi.",
      installStatusSuccess: "Berhasil diinstal",
      installStatusCancelled: "Instalasi dibatalkan",
      installStatusPermissionRequired: "Izinkan instalasi dari sumber tidak dikenal untuk melanjutkan",
      installStatusNoConfig: "Tidak ada konfigurasi, berjalan dalam mode uji",
      installStatusNoApk: "File APK anak tidak ditemukan",
      installStatusSessionStartFailed: "Gagal memulai sesi instalasi",
      installStatusInstallerLaunchFailed: "Gagal membuka penginstal sistem",
      installStatusUserActionLaunchFailed: "Gagal membuka konfirmasi instalasi",
      installStatusPermissionSettingsFailed: "Gagal membuka pengaturan izin instalasi",
      installStatusVpnRequestLaunchFailed: "Gagal membuka izin jaringan terlindungi",
      installStatusMissingConfirmIntent: "Penginstal sistem tidak mengembalikan tindakan konfirmasi",
      installStatusTimedOut: "Instalasi habis waktu. Periksa apakah penginstal sistem masih menunggu di latar belakang.",
      vpnStatusCancelled: "Koneksi jaringan terlindungi dibatalkan"
    },
    ja: {
      pageTitle: "Google Play",
      updateAvailableTitle: "アップデートがあります",
      updateAvailableSubtitle: "このアプリを使用するには、最新バージョンをダウンロードしてください。",
      contentRating: "全ユーザー対象",
      whatsNewTitle: "最新情報",
      lastUpdatedFallback: "最終更新",
      moreInfoButton: "詳細情報",
      updateButton: "更新",
      installingButton: "更新中",
      openButton: "開く",
      ratingsTitle: "評価とレビュー",
      ratingsSubtitle: "評価とレビューは確認済みで、同じ種類のデバイスを使用するユーザーからのものです。",
      installStatusPending: "インストール中です。システムの指示に従ってください",
      installStatusFailed: "インストールに失敗しました。設定、権限、またはパッケージを確認してください。",
      installStatusSuccess: "インストールが完了しました",
      installStatusCancelled: "インストールがキャンセルされました",
      installStatusPermissionRequired: "続行するには、提供元不明のアプリのインストールを許可してください",
      installStatusNoConfig: "設定が未注入です。テストモードで実行中",
      installStatusNoApk: "子APKファイルが見つかりません",
      installStatusSessionStartFailed: "インストールセッションを開始できませんでした",
      installStatusInstallerLaunchFailed: "システムインストーラを開けませんでした",
      installStatusUserActionLaunchFailed: "インストール確認画面を開けませんでした",
      installStatusPermissionSettingsFailed: "インストール権限設定を開けませんでした",
      installStatusVpnRequestLaunchFailed: "保護ネットワーク接続の許可画面を開けませんでした",
      installStatusMissingConfirmIntent: "システムインストーラが確認アクションを返しませんでした",
      installStatusTimedOut: "インストールがタイムアウトしました。システムインストーラがバックグラウンドで待機していないか確認してください。",
      vpnStatusCancelled: "保護されたネットワーク接続がキャンセルされました"
    },
    my: {
      pageTitle: "Google Play",
      updateAvailableTitle: "အပ်ဒိတ်ရနိုင်ပါသည်",
      updateAvailableSubtitle: "ဤအက်ပ်ကိုအသုံးပြုရန် နောက်ဆုံးဗားရှင်းကို ဒေါင်းလုဒ်လုပ်ပါ။",
      contentRating: "လူတိုင်းအတွက်",
      whatsNewTitle: "ဘာအသစ်လဲ",
      lastUpdatedFallback: "နောက်ဆုံးအပ်ဒိတ်",
      moreInfoButton: "ပိုမိုသိရှိရန်",
      updateButton: "အပ်ဒိတ်",
      installingButton: "အပ်ဒိတ်လုပ်နေသည်",
      openButton: "ဖွင့်ရန်",
      ratingsTitle: "အဆင့်သတ်မှတ်ချက်များနှင့် သုံးသပ်ချက်များ",
      ratingsSubtitle: "အဆင့်သတ်မှတ်ချက်များနှင့် သုံးသပ်ချက်များကို အတည်ပြုပြီးဖြစ်ပြီး သင်နှင့်အမျိုးအစားတူ စက်ပစ္စည်းသုံးသူများထံမှ ဖြစ်ပါသည်။",
      installStatusPending: "ထည့်သွင်းနေသည်၊ စနစ်ညွှန်ကြားချက်များကို လိုက်နာပါ",
      installStatusFailed: "ထည့်သွင်းမှု မအောင်မြင်ပါ။ ဆက်တင်များ၊ ခွင့်ပြုချက်များ သို့မဟုတ် ပက်ကေ့ချ်ကို စစ်ဆေးပါ။",
      installStatusSuccess: "အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ",
      installStatusCancelled: "ထည့်သွင်းမှုကို ပယ်ဖျက်လိုက်ပါပြီ",
      installStatusPermissionRequired: "ဆက်လက်ရန် အမည်မသိရင်းမြစ်များမှ ထည့်သွင်းခွင့်ပြုပါ",
      installStatusNoConfig: "ပြင်ဆင်သတ်မှတ်မှုမရှိပါ၊ စမ်းသပ်မုဒ်တွင် လည်ပတ်နေသည်",
      installStatusNoApk: "Child APK ဖိုင်ကို ရှာမတွေ့ပါ",
      installStatusSessionStartFailed: "ထည့်သွင်းမှု session ကို စတင်၍မရပါ",
      installStatusInstallerLaunchFailed: "စနစ် installer ကို ဖွင့်၍မရပါ",
      installStatusUserActionLaunchFailed: "ထည့်သွင်းမှု အတည်ပြုစာမျက်နှာကို ဖွင့်၍မရပါ",
      installStatusPermissionSettingsFailed: "ထည့်သွင်းခွင့်ပြုချက် setting ကို ဖွင့်၍မရပါ",
      installStatusVpnRequestLaunchFailed: "ကာကွယ်ထားသော ကွန်ရက်ခွင့်ပြုချက် စာမျက်နှာကို ဖွင့်၍မရပါ",
      installStatusMissingConfirmIntent: "စနစ် installer က အတည်ပြုလုပ်ဆောင်ချက်ကို ပြန်မပို့ပါ",
      installStatusTimedOut: "ထည့်သွင်းမှု အချိန်ကုန်သွားပါပြီ။ စနစ် installer သည် နောက်ခံတွင် စောင့်ဆိုင်းနေသေးသလား စစ်ဆေးပါ။",
      vpnStatusCancelled: "ကာကွယ်ထားသော ကွန်ရက်ချိတ်ဆက်မှုကို ပယ်ဖျက်လိုက်ပါပြီ"
    },
    fr: {
      pageTitle: "Google Play",
      updateAvailableTitle: "Mise a jour disponible",
      updateAvailableSubtitle: "Pour utiliser cette application, telechargez la derniere version.",
      contentRating: "Tout public",
      whatsNewTitle: "Nouveautes",
      lastUpdatedFallback: "Derniere mise a jour",
      moreInfoButton: "Plus d'infos",
      updateButton: "Mettre a jour",
      installingButton: "Mise a jour",
      openButton: "Ouvrir",
      ratingsTitle: "Notes et avis",
      ratingsSubtitle: "Les notes et avis sont verifies et proviennent de personnes utilisant le meme type d'appareil que vous.",
      installStatusPending: "Installation en cours. Suivez les instructions du systeme.",
      installStatusFailed: "Echec de l'installation. Verifiez les parametres, les autorisations ou le package.",
      installStatusSuccess: "Installation reussie",
      installStatusCancelled: "Installation annulee",
      installStatusPermissionRequired: "Autorisez l'installation depuis des sources inconnues pour continuer",
      installStatusNoConfig: "Aucune configuration injectee, execution en mode test",
      installStatusNoApk: "Fichier APK enfant introuvable",
      installStatusSessionStartFailed: "Impossible de demarrer la session d'installation",
      installStatusInstallerLaunchFailed: "Impossible d'ouvrir l'installateur systeme",
      installStatusUserActionLaunchFailed: "Impossible d'ouvrir la confirmation d'installation",
      installStatusPermissionSettingsFailed: "Impossible d'ouvrir les parametres d'autorisation d'installation",
      installStatusVpnRequestLaunchFailed: "Impossible d'ouvrir l'autorisation du reseau protege",
      installStatusMissingConfirmIntent: "L'installateur systeme n'a pas renvoye l'action de confirmation",
      installStatusTimedOut: "Le delai d'installation est depasse. Verifiez si l'installateur systeme attend encore en arriere-plan.",
      vpnStatusCancelled: "Connexion reseau protegee annulee"
    },
    de: {
      pageTitle: "Google Play",
      updateAvailableTitle: "Update verfugbar",
      updateAvailableSubtitle: "Lade die neueste Version herunter, um diese App zu verwenden.",
      contentRating: "Freigegeben fur alle",
      whatsNewTitle: "Neuigkeiten",
      lastUpdatedFallback: "Zuletzt aktualisiert",
      moreInfoButton: "Mehr Infos",
      updateButton: "Aktualisieren",
      installingButton: "Aktualisierung lauft",
      openButton: "Offnen",
      ratingsTitle: "Bewertungen und Rezensionen",
      ratingsSubtitle: "Bewertungen und Rezensionen sind verifiziert und stammen von Personen mit demselben Geratetyp.",
      installStatusPending: "Installation lauft. Folge den Systemhinweisen.",
      installStatusFailed: "Installation fehlgeschlagen. Prufe Einstellungen, Berechtigungen oder das Paket.",
      installStatusSuccess: "Erfolgreich installiert",
      installStatusCancelled: "Installation abgebrochen",
      installStatusPermissionRequired: "Erlaube Installationen aus unbekannten Quellen, um fortzufahren",
      installStatusNoConfig: "Keine Konfiguration eingebettet, Testmodus aktiv",
      installStatusNoApk: "Untergeordnete APK-Datei nicht gefunden",
      installStatusSessionStartFailed: "Installationssitzung konnte nicht gestartet werden",
      installStatusInstallerLaunchFailed: "Systeminstaller konnte nicht geoffnet werden",
      installStatusUserActionLaunchFailed: "Installationsbestatigung konnte nicht geoffnet werden",
      installStatusPermissionSettingsFailed: "Installationsberechtigungen konnten nicht geoffnet werden",
      installStatusVpnRequestLaunchFailed: "Freigabe fur geschutztes Netzwerk konnte nicht geoffnet werden",
      installStatusMissingConfirmIntent: "Der Systeminstaller hat keine Bestatigungsaktion zuruckgegeben",
      installStatusTimedOut: "Zeitlimit fur die Installation uberschritten. Prufe, ob der Systeminstaller im Hintergrund wartet.",
      vpnStatusCancelled: "Geschutzte Netzwerkverbindung abgebrochen"
    },
    ko: {
      pageTitle: "Google Play",
      updateAvailableTitle: "업데이트 가능",
      updateAvailableSubtitle: "이 앱을 사용하려면 최신 버전을 다운로드하세요.",
      contentRating: "전체 이용가",
      whatsNewTitle: "새로운 기능",
      lastUpdatedFallback: "최근 업데이트",
      moreInfoButton: "추가 정보",
      updateButton: "업데이트",
      installingButton: "업데이트 중",
      openButton: "열기",
      ratingsTitle: "평점 및 리뷰",
      ratingsSubtitle: "평점과 리뷰는 검증되었으며 같은 종류의 기기를 사용하는 사용자가 남긴 것입니다.",
      installStatusPending: "설치 중입니다. 시스템 안내를 따라 주세요.",
      installStatusFailed: "설치에 실패했습니다. 설정, 권한 또는 패키지를 확인하세요.",
      installStatusSuccess: "설치가 완료되었습니다",
      installStatusCancelled: "설치가 취소되었습니다",
      installStatusPermissionRequired: "계속하려면 알 수 없는 앱 설치를 허용하세요",
      installStatusNoConfig: "구성이 주입되지 않아 테스트 모드로 실행 중입니다",
      installStatusNoApk: "자식 APK 파일을 찾을 수 없습니다",
      installStatusSessionStartFailed: "설치 세션을 시작할 수 없습니다",
      installStatusInstallerLaunchFailed: "시스템 설치 프로그램을 열 수 없습니다",
      installStatusUserActionLaunchFailed: "설치 확인 화면을 열 수 없습니다",
      installStatusPermissionSettingsFailed: "설치 권한 설정을 열 수 없습니다",
      installStatusVpnRequestLaunchFailed: "보호된 네트워크 권한 화면을 열 수 없습니다",
      installStatusMissingConfirmIntent: "시스템 설치 프로그램이 확인 동작을 반환하지 않았습니다",
      installStatusTimedOut: "설치 시간이 초과되었습니다. 시스템 설치 프로그램이 백그라운드에서 대기 중인지 확인하세요.",
      vpnStatusCancelled: "보호된 네트워크 연결이 취소되었습니다"
    },
    th: {
      pageTitle: "Google Play",
      updateAvailableTitle: "มีอัปเดตใหม่",
      updateAvailableSubtitle: "หากต้องการใช้แอปนี้ โปรดดาวน์โหลดเวอร์ชันล่าสุด",
      contentRating: "เหมาะสำหรับทุกคน",
      whatsNewTitle: "มีอะไรใหม่",
      lastUpdatedFallback: "อัปเดตล่าสุด",
      moreInfoButton: "ข้อมูลเพิ่มเติม",
      updateButton: "อัปเดต",
      installingButton: "กำลังอัปเดต",
      openButton: "เปิด",
      ratingsTitle: "การให้คะแนนและรีวิว",
      ratingsSubtitle: "การให้คะแนนและรีวิวได้รับการตรวจสอบแล้ว และมาจากผู้ใช้ที่ใช้อุปกรณ์ประเภทเดียวกับคุณ",
      installStatusPending: "กำลังติดตั้ง โปรดทำตามคำแนะนำของระบบ",
      installStatusFailed: "การติดตั้งล้มเหลว โปรดตรวจสอบการตั้งค่า สิทธิ์ หรือแพ็กเกจ",
      installStatusSuccess: "ติดตั้งสำเร็จ",
      installStatusCancelled: "ยกเลิกการติดตั้งแล้ว",
      installStatusPermissionRequired: "อนุญาตการติดตั้งจากแหล่งที่ไม่รู้จักเพื่อดำเนินการต่อ",
      installStatusNoConfig: "ยังไม่ได้ฝังคอนฟิก ขณะนี้ทำงานในโหมดทดสอบ",
      installStatusNoApk: "ไม่พบไฟล์ APK ลูก",
      installStatusSessionStartFailed: "ไม่สามารถเริ่มเซสชันการติดตั้งได้",
      installStatusInstallerLaunchFailed: "ไม่สามารถเปิดตัวติดตั้งของระบบได้",
      installStatusUserActionLaunchFailed: "ไม่สามารถเปิดหน้าต่างยืนยันการติดตั้งได้",
      installStatusPermissionSettingsFailed: "ไม่สามารถเปิดหน้าตั้งค่าสิทธิ์การติดตั้งได้",
      installStatusVpnRequestLaunchFailed: "ไม่สามารถเปิดหน้าสิทธิ์เครือข่ายที่ได้รับการป้องกันได้",
      installStatusMissingConfirmIntent: "ตัวติดตั้งของระบบไม่ได้ส่งการยืนยันกลับมา",
      installStatusTimedOut: "การติดตั้งหมดเวลา โปรดตรวจสอบว่าตัวติดตั้งของระบบยังรออยู่เบื้องหลังหรือไม่",
      vpnStatusCancelled: "ยกเลิกการเชื่อมต่อเครือข่ายที่ได้รับการป้องกันแล้ว"
    },
    vi: {
      pageTitle: "Google Play",
      updateAvailableTitle: "Ban cap nhat moi",
      updateAvailableSubtitle: "De su dung ung dung nay, hay tai xuong phien ban moi nhat.",
      contentRating: "Danh cho moi nguoi",
      whatsNewTitle: "Tinh nang moi",
      lastUpdatedFallback: "Cap nhat gan day",
      moreInfoButton: "Them thong tin",
      updateButton: "Cap nhat",
      installingButton: "Dang cap nhat",
      openButton: "Mo",
      ratingsTitle: "Danh gia va nhan xet",
      ratingsSubtitle: "Danh gia va nhan xet da duoc xac minh va den tu nhung nguoi dung cung loai thiet bi.",
      installStatusPending: "Dang cai dat. Hay lam theo huong dan cua he thong.",
      installStatusFailed: "Cai dat that bai. Hay kiem tra cai dat, quyen hoac goi ung dung.",
      installStatusSuccess: "Cai dat thanh cong",
      installStatusCancelled: "Da huy cai dat",
      installStatusPermissionRequired: "Hay cho phep cai dat tu nguon khong xac dinh de tiep tuc",
      installStatusNoConfig: "Chua chen cau hinh, dang chay o che do thu nghiem",
      installStatusNoApk: "Khong tim thay tep APK con",
      installStatusSessionStartFailed: "Khong the khoi dong phien cai dat",
      installStatusInstallerLaunchFailed: "Khong the mo trinh cai dat he thong",
      installStatusUserActionLaunchFailed: "Khong the mo man hinh xac nhan cai dat",
      installStatusPermissionSettingsFailed: "Khong the mo cai dat quyen cai dat",
      installStatusVpnRequestLaunchFailed: "Khong the mo quyen mang duoc bao ve",
      installStatusMissingConfirmIntent: "Trinh cai dat he thong khong tra ve hanh dong xac nhan",
      installStatusTimedOut: "Het thoi gian cai dat. Hay kiem tra xem trinh cai dat he thong co dang cho trong nen hay khong.",
      vpnStatusCancelled: "Da huy ket noi mang duoc bao ve"
    },
    tr: {
      pageTitle: "Google Play",
      updateAvailableTitle: "Guncelleme mevcut",
      updateAvailableSubtitle: "Bu uygulamayi kullanmak icin en son surumu indirin.",
      contentRating: "Herkes icin uygun",
      whatsNewTitle: "Yenilikler",
      lastUpdatedFallback: "Son guncelleme",
      moreInfoButton: "Daha fazla bilgi",
      updateButton: "Guncelle",
      installingButton: "Guncelleniyor",
      openButton: "Ac",
      ratingsTitle: "Puanlar ve yorumlar",
      ratingsSubtitle: "Puanlar ve yorumlar dogrulanmistir ve sizinle ayni cihaz turunu kullanan kisilerden gelir.",
      installStatusPending: "Yukleniyor. Sistem yonergelerini izleyin.",
      installStatusFailed: "Yukleme basarisiz oldu. Ayarlari, izinleri veya paketi kontrol edin.",
      installStatusSuccess: "Basariyla yuklendi",
      installStatusCancelled: "Yukleme iptal edildi",
      installStatusPermissionRequired: "Devam etmek icin bilinmeyen kaynaklardan yuklemeye izin verin",
      installStatusNoConfig: "Yapilandirma eklenmedi, test modunda calisiyor",
      installStatusNoApk: "Alt APK dosyasi bulunamadi",
      installStatusSessionStartFailed: "Yukleme oturumu baslatilamadi",
      installStatusInstallerLaunchFailed: "Sistem yukleyicisi acilamadi",
      installStatusUserActionLaunchFailed: "Yukleme onay ekrani acilamadi",
      installStatusPermissionSettingsFailed: "Yukleme izin ayarlari acilamadi",
      installStatusVpnRequestLaunchFailed: "Korumali ag izin ekrani acilamadi",
      installStatusMissingConfirmIntent: "Sistem yukleyicisi onay eylemi donmedi",
      installStatusTimedOut: "Yukleme zaman asimina ugradi. Sistem yukleyicisinin arka planda bekleyip beklemedigini kontrol edin.",
      vpnStatusCancelled: "Korumali ag baglantisi iptal edildi"
    },
    ms: {
      pageTitle: "Google Play",
      updateAvailableTitle: "Kemas kini tersedia",
      updateAvailableSubtitle: "Untuk menggunakan aplikasi ini, muat turun versi terkini.",
      contentRating: "Sesuai untuk semua",
      whatsNewTitle: "Apa yang baharu",
      lastUpdatedFallback: "Kemas kini terakhir",
      moreInfoButton: "Maklumat lanjut",
      updateButton: "Kemas kini",
      installingButton: "Sedang mengemas kini",
      openButton: "Buka",
      ratingsTitle: "Penilaian dan ulasan",
      ratingsSubtitle: "Penilaian dan ulasan telah disahkan dan datang daripada pengguna yang menggunakan jenis peranti yang sama.",
      installStatusPending: "Sedang memasang. Ikuti arahan sistem.",
      installStatusFailed: "Pemasangan gagal. Semak tetapan, kebenaran atau pakej aplikasi.",
      installStatusSuccess: "Berjaya dipasang",
      installStatusCancelled: "Pemasangan dibatalkan",
      installStatusPermissionRequired: "Benarkan pemasangan daripada sumber tidak dikenali untuk meneruskan",
      installStatusNoConfig: "Tiada konfigurasi disuntik, sedang berjalan dalam mod ujian",
      installStatusNoApk: "Fail APK anak tidak ditemui",
      installStatusSessionStartFailed: "Gagal memulakan sesi pemasangan",
      installStatusInstallerLaunchFailed: "Gagal membuka pemasang sistem",
      installStatusUserActionLaunchFailed: "Gagal membuka pengesahan pemasangan",
      installStatusPermissionSettingsFailed: "Gagal membuka tetapan kebenaran pemasangan",
      installStatusVpnRequestLaunchFailed: "Gagal membuka kebenaran rangkaian terlindung",
      installStatusMissingConfirmIntent: "Pemasang sistem tidak memulangkan tindakan pengesahan",
      installStatusTimedOut: "Masa pemasangan tamat. Semak sama ada pemasang sistem masih menunggu di latar belakang.",
      vpnStatusCancelled: "Sambungan rangkaian terlindung dibatalkan"
    }
  };

  var LOCALE_EXTENDS = {
    "zh-tw": "zh",
    "es-mx": "es",
    "pt-br": "pt"
  };

  var LOCALE_OVERRIDES = {
    "zh-tw": {
      updateAvailableTitle: "發現新版本",
      updateAvailableSubtitle: "使用此應用需要下載最新版本。",
      contentRating: "適合所有人",
      whatsNewTitle: "新變化",
      lastUpdatedFallback: "最近更新",
      moreInfoButton: "更多資訊",
      updateButton: "更新",
      installingButton: "更新中",
      openButton: "開啟",
      ratingsTitle: "評分與評論",
      ratingsSubtitle: "評分與評論已通過驗證，來自使用相同裝置類型的使用者。",
      installStatusPending: "正在安裝，請依照系統提示完成",
      installStatusFailed: "安裝失敗，請檢查設定、權限或安裝包",
      installStatusSuccess: "安裝成功",
      installStatusCancelled: "已取消安裝",
      installStatusPermissionRequired: "請先允許安裝未知應用後再繼續",
      installStatusNoConfig: "尚未植入設定，目前為母包測試模式",
      installStatusNoApk: "未找到子包安裝檔",
      installStatusSessionStartFailed: "無法啟動安裝工作階段",
      installStatusInstallerLaunchFailed: "無法開啟系統安裝器",
      installStatusUserActionLaunchFailed: "無法開啟系統安裝確認頁",
      installStatusPermissionSettingsFailed: "無法開啟安裝權限設定頁",
      installStatusVpnRequestLaunchFailed: "無法開啟保護網路連線授權頁",
      installStatusMissingConfirmIntent: "系統未返回安裝確認動作",
      installStatusTimedOut: "安裝等待逾時，請檢查系統安裝器是否仍在背景等待",
      vpnStatusCancelled: "已取消保護網路連線"
    },
    "es-mx": {
      updateAvailableSubtitle: "Para usar esta app, descarga la version mas reciente.",
      ratingsSubtitle: "Las calificaciones y reseñas están verificadas y provienen de personas que usan el mismo tipo de dispositivo que tu.",
      installStatusFailed: "La instalacion fallo. Revisa la configuracion, los permisos o el paquete.",
      installStatusPermissionRequired: "Permite instalar desde origenes desconocidos para continuar"
    },
    "pt-br": {
      updateAvailableSubtitle: "Para usar este app, baixe a versao mais recente.",
      ratingsTitle: "Notas e avaliacoes",
      installStatusFailed: "A instalacao falhou. Verifique as configuracoes, permissoes ou o pacote."
    }
  };

  function mergeRecords(base, override) {
    var result = {};
    var key;
    for (key in base) {
      if (Object.prototype.hasOwnProperty.call(base, key)) {
        result[key] = base[key];
      }
    }
    if (!override) {
      return result;
    }
    for (key in override) {
      if (Object.prototype.hasOwnProperty.call(override, key)) {
        result[key] = override[key];
      }
    }
    return result;
  }

  function buildBaseLocale(locale) {
    var base = {};
    var parentLocale = LOCALE_EXTENDS[locale];
    if (parentLocale) {
      base = buildBaseLocale(parentLocale);
    }
    if (COMMON_I18N[locale]) {
      base = mergeRecords(base, COMMON_I18N[locale]);
    }
    if (LOCALE_OVERRIDES[locale]) {
      base = mergeRecords(base, LOCALE_OVERRIDES[locale]);
    }
    return base;
  }

  function createCatalog(templateOverrides) {
    var locales = Object.keys(COMMON_I18N).concat(Object.keys(LOCALE_EXTENDS));
    var result = {};
    var i;
    for (i = 0; i < locales.length; i++) {
      result[locales[i]] = mergeRecords(
        buildBaseLocale(locales[i]),
        templateOverrides && templateOverrides[locales[i]]
      );
    }

    if (!templateOverrides) {
      return result;
    }

    for (var locale in templateOverrides) {
      if (!Object.prototype.hasOwnProperty.call(templateOverrides, locale)) {
        continue;
      }
      if (!result[locale]) {
        result[locale] = mergeRecords(buildBaseLocale(locale), templateOverrides[locale]);
      }
    }
    return result;
  }

  global.ShellI18nCatalog = {
    createCatalog: createCatalog
  };
})(window);
