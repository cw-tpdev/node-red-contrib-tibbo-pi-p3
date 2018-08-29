module.exports = function (RED) {
    "use strict";

    // #07 Two solid state relays

    var TpCommon = require('./tpCommon');

    function TP_07_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp07_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();
    }
    RED.nodes.registerType("Tibbit-#07 out", TP_07_OutNode);
}
