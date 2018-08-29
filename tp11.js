module.exports = function (RED) {
    "use strict";

    // #11 Four open collector outputs

    var TpCommon = require('./tpCommon');

    function TP_11_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp11_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();
    }
    RED.nodes.registerType("Tibbit-#11 out", TP_11_OutNode);
}
