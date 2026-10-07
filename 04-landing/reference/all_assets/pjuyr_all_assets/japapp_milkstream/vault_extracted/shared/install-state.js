(function () {
  "use strict";

  var STATE_MESSAGE_MAP = {
    installing: "installStatusPending",
    success: "installStatusSuccess"
  };

  var ACTION_REASON_MESSAGE_MAP = {
    unknown_sources_permission: "installStatusPermissionRequired"
  };

  var FAILURE_REASON_MESSAGE_MAP = {
    config_missing: "installStatusNoConfig",
    apk_missing: "installStatusNoApk",
    vpn_cancelled: "vpnStatusCancelled",
    vpn_request_launch_failed: "installStatusVpnRequestLaunchFailed",
    install_permission_denied: "installStatusPermissionRequired",
    install_permission_launch_failed: "installStatusPermissionSettingsFailed",
    session_start_failed: "installStatusSessionStartFailed",
    installer_launch_failed: "installStatusInstallerLaunchFailed",
    user_action_launch_failed: "installStatusUserActionLaunchFailed",
    missing_confirm_intent: "installStatusMissingConfirmIntent",
    user_cancelled: "installStatusCancelled",
    install_timeout: "installStatusTimedOut",
    installer_reported_failure: "installStatusFailed",
    unknown: "installStatusFailed"
  };
  var fakeProgress = 0;
  var progressTimer = null;

  function getNode(id) {
    return id ? document.getElementById(id) : null;
  }

  function resolveText(value) {
    return value != null && value !== "" ? value : "";
  }

  function setButtonText(button, value) {
    if (button && value != null && value !== "") {
      button.textContent = value;
    }
  }

  function show(node) {
    if (node) {
      node.removeAttribute("hidden");
    }
  }

  function hide(node) {
    if (node) {
      node.setAttribute("hidden", "hidden");
    }
  }

  function removeClass(node, className) {
    if (node && className) {
      node.classList.remove(className);
    }
  }

  function addClass(node, className) {
    if (node && className) {
      node.classList.add(className);
    }
  }

  function normalizePayload(stateOrPayload, reason, message) {
    if (stateOrPayload && typeof stateOrPayload === "object") {
      return {
        state: resolveText(stateOrPayload.state),
        reason: resolveText(stateOrPayload.reason),
        message: resolveText(stateOrPayload.message)
      };
    }

    var state = resolveText(stateOrPayload);
    var normalized = {
      state: state,
      reason: resolveText(reason),
      message: resolveText(message)
    };
    return normalized;
  }

  function combineMessage(primary, detail) {
    var primaryText = resolveText(primary);
    var detailText = resolveText(detail);
    if (!primaryText) {
      return detailText;
    }
    if (!detailText || detailText === primaryText) {
      return primaryText;
    }
    return primaryText + "\n" + detailText;
  }

  function getStateMessage(config, payload) {
    var i18n = config.i18n || {};
    if (payload.state === "action_required") {
      var actionKey = ACTION_REASON_MESSAGE_MAP[payload.reason];
      var actionMessage = actionKey && i18n[actionKey] ? i18n[actionKey] : "";
      return combineMessage(actionMessage, payload.message);
    }
    if (payload.state === "failure") {
      var reasonKey = FAILURE_REASON_MESSAGE_MAP[payload.reason];
      var reasonMessage = reasonKey && i18n[reasonKey] ? i18n[reasonKey] : (i18n.installStatusFailed || "");
      return combineMessage(reasonMessage, payload.message);
    }
    var i18nKey = STATE_MESSAGE_MAP[payload.state];
    return i18nKey && i18n[i18nKey] ? i18n[i18nKey] : payload.message;
  }

  function getInstallButtons(config) {
    var ids = [config.installButtonId].concat(config.additionalInstallButtonIds || []);
    return ids.map(getNode).filter(function (button) { return button !== null; });
  }

  function setButtonsDisabled(buttons, disabled) {
    buttons.forEach(function (button) {
      button.disabled = disabled;
    });
  }

  function requestInstall(buttons) {
    var enabled = buttons.some(function (button) { return !button.disabled; });
    if (!enabled) {
      return;
    }
    setButtonsDisabled(buttons, true);
    try {
      if (window.ShellBridge && window.ShellBridge.requestInstall) {
        window.ShellBridge.requestInstall();
      }
    } catch (error) {
      setButtonsDisabled(buttons, false);
    }
  }

  function bindInstallButtons(config) {
    var buttons = getInstallButtons(config);
    var primaryButton = getNode(config.installButtonId);
    if (!primaryButton || buttons.length === 0) {
      return;
    }
    setButtonText(primaryButton, config.updateButtonLabel);
    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        requestInstall(buttons);
      });
    });
  }

  function bindDebugEntry(config) {
    var target = getNode(config.debugEntryTargetId);
    if (!target) {
      return;
    }
    target.addEventListener("click", function () {
      try {
        if (window.ShellBridge && window.ShellBridge.notifyDebugEntryTap) {
          window.ShellBridge.notifyDebugEntryTap();
        }
      } catch (error) {
        if (window.console && window.console.warn) {
          window.console.warn("[shell-install-state] notifyDebugEntryTap failed", error);
        }
      }
    });
  }

  function setProgress(progressBar, value) {
    fakeProgress = Math.max(0, Math.min(100, value));
    if (progressBar) {
      progressBar.style.width = fakeProgress.toFixed(1) + "%";
    }
  }

  function stopFakeProgress() {
    if (progressTimer !== null) {
      window.clearInterval(progressTimer);
      progressTimer = null;
    }
  }

  function startFakeProgress(progressBar) {
    if (fakeProgress < 5) {
      setProgress(progressBar, 5);
    }
    if (progressTimer !== null) {
      return;
    }
    progressTimer = window.setInterval(function () {
      var remaining = 92 - fakeProgress;
      if (remaining <= 0) {
        stopFakeProgress();
        return;
      }
      setProgress(progressBar, fakeProgress + Math.max(0.4, remaining * 0.06));
    }, 650);
  }

  function resetStatus(config, nodes) {
    stopFakeProgress();
    setProgress(nodes.progressBar, 0);
    hide(nodes.statusBar);
    nodes.statusText.textContent = "";
    setButtonsDisabled(nodes.installButtons, false);
    setButtonText(nodes.installButton, config.updateButtonLabel);
  }

  function setStatus(config, stateOrPayload, reason, message) {
    var nodes = {
      statusBar: getNode(config.statusBarId),
      statusText: getNode(config.statusTextId),
      progressBar: getNode(config.progressBarId),
      installButton: getNode(config.installButtonId),
      installButtons: getInstallButtons(config)
    };
    if (!nodes.statusBar || !nodes.statusText || !nodes.installButton) {
      return;
    }

    removeClass(nodes.statusBar, config.errorClass);
    removeClass(nodes.statusBar, config.successClass);
    removeClass(nodes.progressBar, config.loadingClass);

    var payload = normalizePayload(stateOrPayload, reason, message);
    var displayMessage = getStateMessage(config, payload);

    if (payload.state === "installing") {
      show(nodes.statusBar);
      nodes.statusText.textContent = displayMessage;
      setButtonsDisabled(nodes.installButtons, true);
      setButtonText(nodes.installButton, config.installingButtonLabel);
      if (payload.reason === "waiting_result" || payload.reason === "verifying_result") {
        addClass(nodes.progressBar, config.loadingClass);
        startFakeProgress(nodes.progressBar);
      } else {
        stopFakeProgress();
      }
      return;
    }

    if (payload.state === "action_required") {
      show(nodes.statusBar);
      nodes.statusText.textContent = displayMessage;
      stopFakeProgress();
      setButtonsDisabled(nodes.installButtons, true);
      setButtonText(nodes.installButton, config.updateButtonLabel);
      return;
    }

    if (payload.state === "success") {
      show(nodes.statusBar);
      addClass(nodes.statusBar, config.successClass);
      nodes.statusText.textContent = displayMessage;
      stopFakeProgress();
      setProgress(nodes.progressBar, 100);
      setButtonsDisabled(nodes.installButtons, true);
      setButtonText(nodes.installButton, config.openButtonLabel);
      return;
    }

    if (payload.state === "failure") {
      show(nodes.statusBar);
      addClass(nodes.statusBar, config.errorClass);
      nodes.statusText.textContent = displayMessage;
      stopFakeProgress();
      setProgress(nodes.progressBar, 0);
      setButtonsDisabled(nodes.installButtons, false);
      setButtonText(nodes.installButton, config.updateButtonLabel);
      return;
    }

    resetStatus(config, nodes);
  }

  function bind(config) {
    var normalizedConfig = config || {};
    normalizedConfig.updateButtonLabel = resolveText(normalizedConfig.updateButtonLabel);
    normalizedConfig.openButtonLabel = resolveText(normalizedConfig.openButtonLabel);
    normalizedConfig.installingButtonLabel = resolveText(normalizedConfig.installingButtonLabel);
    bindInstallButtons(normalizedConfig);
    bindDebugEntry(normalizedConfig);
    window.ShellApp = {
      onState: function (stateOrPayload, reason, message) {
        setStatus(normalizedConfig, stateOrPayload, reason, message);
      }
    };
  }

  function notifyReady() {
    try {
      if (window.ShellBridge && window.ShellBridge.notifyReady) {
        window.ShellBridge.notifyReady();
      }
    } catch (error) {
      if (window.console && window.console.warn) {
        window.console.warn("[shell-install-state] notifyReady failed", error);
      }
    }
  }

  window.ShellInstallState = {
    bind: bind,
    notifyReady: notifyReady
  };
})();
