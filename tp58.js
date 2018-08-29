module.exports = function (RED) {
    "use strict";

    // #58 Two 24V NPN isolated open collector outputs

    var TpCommon = require('./tpCommon');

    function TP_58_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp58_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();
    }
    RED.nodes.registerType("Tibbit-#58 out", TP_58_OutNode);
}
