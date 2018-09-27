module.exports = function (RED) {
    "use strict";

    // TPbit #01 LED

    var TpCommon = require('./tpCommon');

    function TPB_01_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tpb01_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();

    }
    RED.nodes.registerType("TPbit-#01 out", TPB_01_OutNode);
}
