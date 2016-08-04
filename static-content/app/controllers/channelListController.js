myApp.controller('channelListCtrl', ['$scope', '$rootScope', '$resource', '$timeout', function ($scope, $rootScope, $resource, $timeout) {

    $rootScope.backoff_factor = 1.0;

    $scope.ChannelsResource = $resource(API_ENDPOINT + "/channel");
    $scope.channels = [];

    $scope.PopulateChannels = function (Channels) {
        if ($rootScope.chatting) {
            console.log('Retrieving channel list from Server');
            Channels.get(null, function (channels) {
                channels.channels.push(DEFAULT_CHANNEL_NAME);
                console.log(channels.channels);
                if ($rootScope.chatting) {
                    var currentChannel = $rootScope.channel;
                    $scope.channels = channels.channels.filter(function (c) {
                        return c != currentChannel;
                    }).sort();
                    $scope.defaultChannel = [$rootScope.channel];
                }
                else {
                    //just in case, for cleanup
                    $scope.channels = [];
                }
            });
            return true;
        }
        else {
            return false;
        }
    }

    $scope.ChangeChannel = function (c) {
        $rootScope.channel = c;
        $scope.ChannelsResource = $resource(API_ENDPOINT + "/channel");
        $scope.PopulateChannels($scope.ChannelsResource);
        $rootScope.$emit('channelChanged', c);
    }

    $scope.ChannelRefresh = function () {
        $scope.PopulateChannels($scope.ChannelsResource);
        var poll = function () {
            $timeout(function () {
                if ($scope.PopulateChannels($scope.ChannelsResource)) {
                    poll();
                }
            }, 5000 * $rootScope.backoff_factor);
        };
        poll();
    };

    $rootScope.$on("chatting", $scope.ChannelRefresh);

    $rootScope.$on("not chatting", function () {
        //clear our model, which will clear out the channels from the panel
        $scope.channels = null;
        $scope.defaultChannel = null;
    });

    $scope.$on('async_init', $scope.ChannelRefresh);

    if (localStorage.getItem('userName') !== null) {
        $scope.$emit('async_init');
    }
}]);
