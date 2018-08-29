module.exports = function (RED) {
    "use strict";

    // #15 High-voltage AC solid state relay

    var TpCommon = require('./tpCommon');

    function TP_15_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp15_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();
    }
    RED.nodes.registerType("Tibbit-#15 out", TP_15_OutNode);
}
