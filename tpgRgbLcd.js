module.exports = function (RED) {
    "use strict";

    // TP Grove - LCD RGB Backlight

    var TpCommon = require('./tpCommon');

    function TPG_RgbLcd_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tpgRgbLcd_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();

    }
    RED.nodes.registerType("RgbLcd out", TPG_RgbLcd_OutNode);
}
